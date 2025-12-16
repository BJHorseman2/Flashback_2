"""Scene generation service for the worker."""
import os
from typing import Optional
import structlog

from google.cloud import aiplatform
from google.cloud import storage

logger = structlog.get_logger()

# Configuration from environment
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
GCS_BUCKET = os.getenv("GCS_BUCKET", "flashback-assets")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "imagen-3.0-generate-001")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Global style header
GLOBAL_STYLE_HEADER = """Realistic editorial illustration (not a photograph). High detail, naturalistic lighting, subtle paper/ink texture, cinematic composition. No text, no captions, no logos, no watermarks. Faces non-identifiable."""

LENS_SPECS = {
    1: {"name": "Wide", "camera": "wide 35mm lens", "composition": "establishing shot", "focus": "horizon and landmark"},
    2: {"name": "POV", "camera": "shoulder-height eye level", "composition": "witness perspective", "focus": "foreground silhouettes"},
    3: {"name": "Detail", "camera": "macro close-up lens", "composition": "tight framing", "focus": "texture detail"},
    4: {"name": "Behind", "camera": "interior medium shot", "composition": "decision room view", "focus": "figures at work"},
    5: {"name": "After", "camera": "wide establishing shot", "composition": "calmer atmosphere", "focus": "aftermath scene"},
}

MAX_RETRIES = 2


class SceneGenerator:
    """Handles image generation for flashback scenes."""

    def __init__(self):
        self._initialized = False

    def _ensure_initialized(self):
        """Initialize GCP clients."""
        if not self._initialized and GCP_PROJECT:
            aiplatform.init(project=GCP_PROJECT, location=GCP_REGION)
            self._initialized = True

    async def generate_all_lenses(self, scene_id: str) -> bool:
        """Generate all 5 lenses for a scene."""
        self._ensure_initialized()

        # Load scene from database
        scene_data = await self._load_scene(scene_id)
        if not scene_data:
            logger.error("scene_not_found", scene_id=scene_id)
            return False

        scene_spec = scene_data.get("scene_spec", {})
        all_success = True

        for lens_id in range(1, 6):
            success = await self._generate_lens_with_qc(scene_id, lens_id, scene_spec)
            if not success:
                all_success = False

        # Update scene status
        await self._update_scene_status(scene_id, "ready" if all_success else "failed")

        return all_success

    async def generate_single_lens(self, scene_id: str, lens_id: int) -> bool:
        """Generate a single lens image."""
        self._ensure_initialized()

        scene_data = await self._load_scene(scene_id)
        if not scene_data:
            return False

        scene_spec = scene_data.get("scene_spec", {})
        return await self._generate_lens_with_qc(scene_id, lens_id, scene_spec)

    async def _generate_lens_with_qc(
        self,
        scene_id: str,
        lens_id: int,
        scene_spec: dict
    ) -> bool:
        """Generate a lens image with QC retries."""
        prompt = self._build_prompt(scene_spec, lens_id)

        for attempt in range(MAX_RETRIES + 1):
            logger.info(
                "generating_lens",
                scene_id=scene_id,
                lens_id=lens_id,
                attempt=attempt + 1
            )

            # Generate image
            image_bytes = await self._generate_image(prompt)
            if not image_bytes:
                continue

            # Run QC
            qc_passed, qc_result = await self._run_qc(image_bytes, scene_spec, lens_id)

            if qc_passed:
                # Upload and save
                url = await self._upload_image(image_bytes, scene_id, lens_id)
                if url:
                    await self._save_asset(scene_id, lens_id, url, qc_result)
                    return True
            else:
                # Build correction prompt
                if attempt < MAX_RETRIES:
                    prompt = self._build_correction_prompt(prompt, qc_result)

        # All attempts failed
        await self._mark_asset_failed(scene_id, lens_id)
        return False

    def _build_prompt(self, scene_spec: dict, lens_id: int) -> str:
        """Build image generation prompt."""
        lens = LENS_SPECS.get(lens_id, LENS_SPECS[1])

        location = scene_spec.get("location", {})
        setting = scene_spec.get("setting", {})

        parts = [
            GLOBAL_STYLE_HEADER,
            "",
            f"Historical recreation of: {scene_spec.get('event_title', 'Historical event')} ({scene_spec.get('year', 'Unknown')}).",
            f"Location: {location.get('name', 'Unknown')}.",
            f"Setting: {setting.get('environment', 'outdoor')}.",
            f"Time: {setting.get('time_of_day', 'day')}.",
            f"Era cues: {', '.join(scene_spec.get('era_cues', []))}.",
            f"Mood: {scene_spec.get('mood', 'uncertain')}.",
            "",
            f"Shot: {lens['name']}.",
            f"Camera: {lens['camera']}.",
            f"Composition: {lens['composition']}.",
            f"Focus: {lens['focus']}.",
            "",
            f"Must include: {', '.join(scene_spec.get('must_include', []))}.",
            f"Must NOT include: {', '.join(scene_spec.get('must_not_include', []))}.",
            "",
            "Avoid identifiable faces. Keep period-accurate props only."
        ]

        return "\n".join(parts)

    def _build_correction_prompt(self, original: str, qc_result: dict) -> str:
        """Build correction prompt from QC failures."""
        issues = qc_result.get("issues", [])
        suggestions = qc_result.get("suggestions", [])

        if suggestions:
            corrections = ". ".join(suggestions[:3])
            return f"{original}\n\nIMPORTANT CORRECTIONS: {corrections}. Keep style."

        return original

    async def _generate_image(self, prompt: str) -> Optional[bytes]:
        """Generate image using Vertex AI."""
        if not GCP_PROJECT:
            logger.warning("gcp_not_configured")
            return None

        try:
            from vertexai.preview.vision_models import ImageGenerationModel

            model = ImageGenerationModel.from_pretrained(IMAGE_MODEL)
            response = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio="16:9",
                safety_filter_level="block_some",
                person_generation="allow_adult"
            )

            if response.images:
                return response.images[0]._image_bytes

            return None
        except Exception as e:
            logger.error("image_generation_error", error=str(e))
            return None

    async def _run_qc(
        self,
        image_bytes: bytes,
        scene_spec: dict,
        lens_id: int
    ) -> tuple[bool, dict]:
        """Run QC checks on generated image."""
        if not GCP_PROJECT:
            return True, {}

        try:
            from vertexai.generative_models import GenerativeModel, Part

            model = GenerativeModel(GEMINI_MODEL)

            qc_prompt = self._build_qc_prompt(scene_spec)
            image_part = Part.from_data(data=image_bytes, mime_type="image/png")

            response = model.generate_content(
                [image_part, qc_prompt],
                generation_config={"temperature": 0.1, "max_output_tokens": 1024}
            )

            return self._parse_qc_response(response.text, scene_spec)

        except Exception as e:
            logger.error("qc_error", error=str(e))
            return True, {}

    def _build_qc_prompt(self, scene_spec: dict) -> str:
        """Build QC analysis prompt."""
        parts = ["Analyze this image. Answer YES or NO for each:"]

        for item in scene_spec.get("must_include", []):
            parts.append(f"- Is '{item}' visible? YES/NO")

        parts.append("- Any readable text? YES/NO")
        parts.append("- Any logos? YES/NO")
        parts.append("- Identifiable faces? YES/NO")
        parts.append("List specific issues if any.")

        return "\n".join(parts)

    def _parse_qc_response(self, response: str, scene_spec: dict) -> tuple[bool, dict]:
        """Parse QC response."""
        result = {"passed": True, "issues": [], "suggestions": []}
        lines = response.lower()

        # Check for failures
        if "readable text" in lines and "yes" in lines:
            result["passed"] = False
            result["issues"].append("Contains readable text")
            result["suggestions"].append("Remove all text")

        if "logos" in lines and "yes" in lines:
            result["passed"] = False
            result["issues"].append("Contains logos")
            result["suggestions"].append("Remove logos")

        if "identifiable" in lines and "yes" in lines:
            result["passed"] = False
            result["issues"].append("Identifiable faces")
            result["suggestions"].append("Make faces indistinct")

        return result["passed"], result

    async def _upload_image(
        self,
        image_bytes: bytes,
        scene_id: str,
        lens_id: int
    ) -> Optional[str]:
        """Upload image to GCS."""
        if not GCP_PROJECT:
            return None

        try:
            import uuid
            client = storage.Client(project=GCP_PROJECT)
            bucket = client.bucket(GCS_BUCKET)

            filename = f"scenes/{scene_id}/lens_{lens_id}_{uuid.uuid4().hex[:8]}.png"
            blob = bucket.blob(filename)
            blob.upload_from_string(image_bytes, content_type="image/png")
            blob.make_public()

            return blob.public_url
        except Exception as e:
            logger.error("upload_error", error=str(e))
            return None

    async def _load_scene(self, scene_id: str) -> Optional[dict]:
        """Load scene from database."""
        # Placeholder - implement actual database query
        return None

    async def _update_scene_status(self, scene_id: str, status: str):
        """Update scene status in database."""
        pass

    async def _save_asset(
        self,
        scene_id: str,
        lens_id: int,
        url: str,
        qc_result: dict
    ):
        """Save asset to database."""
        pass

    async def _mark_asset_failed(self, scene_id: str, lens_id: int):
        """Mark asset as failed in database."""
        pass

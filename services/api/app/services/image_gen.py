"""Image generation service using Vertex AI / Gemini."""
import base64
import uuid
from typing import Optional
import structlog
from google.cloud import aiplatform
from google.cloud import storage

from app.config import get_settings
from app.models.schemas import SceneSpec

logger = structlog.get_logger()

# Global style header for all images
GLOBAL_STYLE_HEADER = """Realistic editorial illustration (not a photograph). High detail, naturalistic lighting, subtle paper/ink texture, cinematic composition. No text, no captions, no logos, no watermarks. Faces non-identifiable."""

# Lens specifications (the 5 Zoom Lens presets)
LENS_SPECS = {
    1: {
        "name": "Wide",
        "camera": "wide 35mm lens",
        "composition": "establishing shot showing full scene",
        "focus": "horizon and key landmark visible"
    },
    2: {
        "name": "POV",
        "camera": "shoulder-height eye level",
        "composition": "witness perspective with mild motion blur",
        "focus": "foreground silhouettes of observers"
    },
    3: {
        "name": "Detail",
        "camera": "macro close-up lens",
        "composition": "tight framing on single object",
        "focus": "texture and detail of key object"
    },
    4: {
        "name": "Behind",
        "camera": "interior medium shot",
        "composition": "decision room or control center view",
        "focus": "figures at work, screens or documents visible"
    },
    5: {
        "name": "After",
        "camera": "wide establishing shot",
        "composition": "same location cues as Lens 1, calmer atmosphere",
        "focus": "aftermath scene, no injuries or gore"
    }
}


class ImageGenerationService:
    """Service for generating images using Vertex AI."""

    def __init__(self):
        self.settings = get_settings()
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of Vertex AI."""
        if not self._initialized and self.settings.gcp_project_id:
            aiplatform.init(
                project=self.settings.gcp_project_id,
                location=self.settings.gcp_region
            )
            self._initialized = True

    def build_prompt(self, scene_spec: SceneSpec, lens_id: int) -> str:
        """
        Build a complete image generation prompt from SceneSpec and lens.

        This is deterministic - same inputs always produce same prompt.
        """
        lens = LENS_SPECS.get(lens_id, LENS_SPECS[1])

        prompt_parts = [
            GLOBAL_STYLE_HEADER,
            "",
            f"Historical recreation of: {scene_spec.event_title} ({scene_spec.year}).",
            f"Location: {scene_spec.location.name}.",
            f"Setting: {scene_spec.setting.environment}.",
            f"Time: {scene_spec.setting.time_of_day}.",
            f"Era cues: {', '.join(scene_spec.era_cues)}.",
            f"Mood: {scene_spec.mood}.",
            "",
            f"Shot: {lens['name']}.",
            f"Camera: {lens['camera']}.",
            f"Composition: {lens['composition']}.",
            f"Focus: {lens['focus']}.",
            "",
            f"Must include: {', '.join(scene_spec.must_include)}.",
            f"Must NOT include: {', '.join(scene_spec.must_not_include)}.",
            "",
            "Avoid identifiable faces (use silhouettes / indistinct features). Keep period-accurate props only."
        ]

        prompt = "\n".join(prompt_parts)

        logger.info("built_prompt", lens_id=lens_id, prompt_length=len(prompt))

        return prompt

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9"
    ) -> Optional[bytes]:
        """
        Generate an image using Vertex AI Imagen.

        Args:
            prompt: The full image generation prompt
            aspect_ratio: Image aspect ratio (16:9 for landscape, 9:16 for portrait)

        Returns:
            Image bytes if successful, None if failed
        """
        self._ensure_initialized()

        if not self.settings.gcp_project_id:
            logger.warning("gcp_not_configured", message="GCP project ID not set")
            return None

        try:
            from vertexai.preview.vision_models import ImageGenerationModel

            model = ImageGenerationModel.from_pretrained(self.settings.image_model)

            response = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_some",
                person_generation="allow_adult"
            )

            if response.images:
                image = response.images[0]
                logger.info("image_generated", size=len(image._image_bytes))
                return image._image_bytes

            logger.warning("no_images_generated")
            return None

        except Exception as e:
            logger.error("image_generation_failed", error=str(e))
            return None

    async def upload_image(
        self,
        image_bytes: bytes,
        scene_id: str,
        lens_id: int
    ) -> Optional[str]:
        """
        Upload generated image to cloud storage.

        Returns the public URL of the uploaded image.
        """
        if not self.settings.gcp_project_id:
            logger.warning("gcp_not_configured")
            return None

        try:
            client = storage.Client(project=self.settings.gcp_project_id)
            bucket = client.bucket(self.settings.gcs_bucket)

            # Generate unique filename
            filename = f"scenes/{scene_id}/lens_{lens_id}_{uuid.uuid4().hex[:8]}.png"
            blob = bucket.blob(filename)

            blob.upload_from_string(
                image_bytes,
                content_type="image/png"
            )

            # Make publicly accessible
            blob.make_public()

            url = blob.public_url
            logger.info("image_uploaded", url=url)
            return url

        except Exception as e:
            logger.error("image_upload_failed", error=str(e))
            return None

    async def generate_and_upload(
        self,
        scene_spec: SceneSpec,
        scene_id: str,
        lens_id: int
    ) -> Optional[str]:
        """
        Generate an image for a lens and upload it.

        Returns the public URL if successful.
        """
        prompt = self.build_prompt(scene_spec, lens_id)

        image_bytes = await self.generate_image(prompt)
        if not image_bytes:
            return None

        return await self.upload_image(image_bytes, scene_id, lens_id)

    def get_lens_name(self, lens_id: int) -> str:
        """Get the display name for a lens."""
        return LENS_SPECS.get(lens_id, LENS_SPECS[1])["name"]


# Singleton instance
_image_service: Optional[ImageGenerationService] = None


def get_image_service() -> ImageGenerationService:
    """Get or create the image generation service instance."""
    global _image_service
    if _image_service is None:
        _image_service = ImageGenerationService()
    return _image_service

"""Quality Control service for validating generated images."""
import base64
from typing import Optional
import structlog
from google.cloud import aiplatform

from app.config import get_settings
from app.models.schemas import SceneSpec

logger = structlog.get_logger()


class QCResult:
    """Result of a QC check on a generated image."""

    def __init__(self):
        self.passed = True
        self.must_include_results: dict[str, bool] = {}
        self.must_not_include_results: dict[str, bool] = {}
        self.has_readable_text = False
        self.has_logos = False
        self.has_identifiable_faces = False
        self.issues: list[str] = []
        self.suggestions: list[str] = []

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "must_include_results": self.must_include_results,
            "must_not_include_results": self.must_not_include_results,
            "has_readable_text": self.has_readable_text,
            "has_logos": self.has_logos,
            "has_identifiable_faces": self.has_identifiable_faces,
            "issues": self.issues,
            "suggestions": self.suggestions
        }


class QualityControlService:
    """
    Service for validating generated images meet SceneSpec requirements.

    QC checks:
    1. must_include items are present
    2. must_not_include items are absent
    3. No readable text
    4. No logos
    5. No identifiable faces
    """

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

    async def check_image(
        self,
        image_bytes: bytes,
        scene_spec: SceneSpec,
        lens_id: int
    ) -> QCResult:
        """
        Run QC checks on a generated image.

        Uses Gemini vision to analyze the image against SceneSpec requirements.
        """
        self._ensure_initialized()
        result = QCResult()

        if not self.settings.gcp_project_id:
            logger.warning("qc_skipped_no_gcp")
            return result

        try:
            from vertexai.generative_models import GenerativeModel, Part

            model = GenerativeModel(self.settings.gemini_model)

            # Build QC prompt
            qc_prompt = self._build_qc_prompt(scene_spec)

            # Create image part
            image_part = Part.from_data(
                data=image_bytes,
                mime_type="image/png"
            )

            response = model.generate_content(
                [image_part, qc_prompt],
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 1024
                }
            )

            # Parse response
            result = self._parse_qc_response(response.text, scene_spec)

            logger.info(
                "qc_check_complete",
                passed=result.passed,
                issues_count=len(result.issues)
            )

        except Exception as e:
            logger.error("qc_check_failed", error=str(e))
            # Don't fail the whole process if QC check fails
            result.issues.append(f"QC check error: {str(e)}")

        return result

    def _build_qc_prompt(self, scene_spec: SceneSpec) -> str:
        """Build the QC analysis prompt."""
        prompt_parts = [
            "Analyze this image for quality control. Answer each question with YES or NO, then brief explanation.",
            "",
            "MUST INCLUDE (should be present):"
        ]

        for item in scene_spec.must_include:
            prompt_parts.append(f"- Is '{item}' visible? YES/NO:")

        prompt_parts.extend([
            "",
            "MUST NOT INCLUDE (should be absent):"
        ])

        for item in scene_spec.must_not_include:
            prompt_parts.append(f"- Is '{item}' present? YES/NO:")

        prompt_parts.extend([
            "",
            "QUALITY CHECKS:",
            "- Is there any readable text in the image? YES/NO:",
            "- Are there any logos or brand marks? YES/NO:",
            "- Are there any identifiable human faces (clear facial features)? YES/NO:",
            "",
            f"- Does the image match the era ({scene_spec.year})? YES/NO:",
            f"- Does the mood feel '{scene_spec.mood}'? YES/NO:",
            "",
            "Finally, list any specific issues that should be fixed in a regeneration."
        ])

        return "\n".join(prompt_parts)

    def _parse_qc_response(self, response_text: str, scene_spec: SceneSpec) -> QCResult:
        """Parse the QC response from Gemini."""
        result = QCResult()
        lines = response_text.lower().split("\n")

        for item in scene_spec.must_include:
            found = self._check_response_for_item(lines, item, expect_yes=True)
            result.must_include_results[item] = found
            if not found:
                result.passed = False
                result.issues.append(f"Missing required element: {item}")
                result.suggestions.append(f"Add {item}")

        for item in scene_spec.must_not_include:
            found = self._check_response_for_item(lines, item, expect_yes=False)
            result.must_not_include_results[item] = not found
            if found:
                result.passed = False
                result.issues.append(f"Contains forbidden element: {item}")
                result.suggestions.append(f"Remove {item}")

        # Check for text
        if self._check_contains(lines, "readable text", "yes"):
            result.has_readable_text = True
            result.passed = False
            result.issues.append("Image contains readable text")
            result.suggestions.append("Remove all readable text")

        # Check for logos
        if self._check_contains(lines, "logos", "yes"):
            result.has_logos = True
            result.passed = False
            result.issues.append("Image contains logos")
            result.suggestions.append("Remove all logos and brand marks")

        # Check for faces
        if self._check_contains(lines, "identifiable", "yes") or self._check_contains(lines, "faces", "yes"):
            result.has_identifiable_faces = True
            result.passed = False
            result.issues.append("Image contains identifiable faces")
            result.suggestions.append("Make faces indistinct or use silhouettes")

        return result

    def _check_response_for_item(self, lines: list[str], item: str, expect_yes: bool) -> bool:
        """Check if an item appears in the response with expected answer."""
        item_lower = item.lower()
        for line in lines:
            if item_lower in line:
                has_yes = "yes" in line
                return has_yes if expect_yes else not has_yes
        return expect_yes  # Default to expected if not found

    def _check_contains(self, lines: list[str], keyword: str, value: str) -> bool:
        """Check if lines contain keyword with specific value."""
        for line in lines:
            if keyword in line and value in line:
                return True
        return False

    def build_correction_prompt(
        self,
        original_prompt: str,
        qc_result: QCResult
    ) -> str:
        """
        Build a correction prompt for regenerating a failed image.

        Adds specific instructions based on QC failures.
        """
        corrections = []

        for suggestion in qc_result.suggestions[:3]:  # Limit to 3 corrections
            corrections.append(suggestion)

        correction_text = ". ".join(corrections)

        return f"{original_prompt}\n\nIMPORTANT CORRECTIONS: {correction_text}. Keep the overall composition and style."


# Singleton instance
_qc_service: Optional[QualityControlService] = None


def get_qc_service() -> QualityControlService:
    """Get or create the QC service instance."""
    global _qc_service
    if _qc_service is None:
        _qc_service = QualityControlService()
    return _qc_service

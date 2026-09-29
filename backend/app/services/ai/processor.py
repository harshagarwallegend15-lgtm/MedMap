import logging

from app.services.ai.config import AIConfig
from app.services.ai.provider import BaseAIProvider
from app.services.ai.mock_provider import MockProvider
from app.services.ai.schemas import (
    ProcessIntakeRequest,
    StructuredClinicalOutput,
    AIOutputStatus,
)

logger = logging.getLogger(__name__)


class AIProcessor:
    """Main entry point for AI processing.

    Selects the configured provider and wraps calls with safe failure handling.
    All output is AI-generated and must be reviewed by a doctor.
    """

    def __init__(self, ai_config: AIConfig | None = None):
        """Initialize with explicit config for testability."""
        self._config = ai_config or AIConfig()
        self.provider: BaseAIProvider = self._create_provider()

    def _create_provider(self) -> BaseAIProvider:
        if self._config.provider == "gemini":
            try:
                from app.services.ai.gemini_provider import GeminiProvider
                return GeminiProvider()
            except Exception as e:
                logger.error(
                    f"Failed to initialize GeminiProvider, "
                    f"falling back to mock: {e}"
                )
                return MockProvider()
        return MockProvider()

    def process_intake(
        self, request: ProcessIntakeRequest
    ) -> StructuredClinicalOutput:
        try:
            result = self.provider.process_case(request)
            # Safety invariant: AI output is NEVER authoritative
            result.is_ai_generated = True
            result.requires_doctor_review = True
            return result
        except Exception as e:
            logger.error(f"Error during AI processing: {e}")
            return StructuredClinicalOutput(
                status=AIOutputStatus.FAILED,
                confidence_score=0.0,
                error_message="Internal processing error",
                is_ai_generated=True,
                requires_doctor_review=True,
            )

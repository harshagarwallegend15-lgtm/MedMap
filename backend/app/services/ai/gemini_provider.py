import json
import logging

import google.generativeai as genai

from app.services.ai.provider import BaseAIProvider
from app.services.ai.schemas import (
    ProcessIntakeRequest,
    StructuredClinicalOutput,
    ClinicalAssessment,
    AIOutputStatus,
)
from app.services.ai.config import config

logger = logging.getLogger(__name__)

# Timeout in seconds for Gemini API calls
_GEMINI_TIMEOUT_SECONDS = 30


class GeminiProvider(BaseAIProvider):
    """Real Gemini provider. Requires GEMINI_API_KEY to be set."""

    def __init__(self):
        if not config.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. "
                "Set it in your environment or .env file."
            )
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def process_case(self, request: ProcessIntakeRequest) -> StructuredClinicalOutput:
        prompt = self._build_prompt(request)
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                ),
                request_options={"timeout": _GEMINI_TIMEOUT_SECONDS},
            )
            return self._parse_response(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned malformed JSON: {e}")
            return StructuredClinicalOutput(
                status=AIOutputStatus.FAILED,
                confidence_score=0.0,
                error_message="AI returned malformed output",
                is_ai_generated=True,
                requires_doctor_review=True,
            )
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            return StructuredClinicalOutput(
                status=AIOutputStatus.FAILED,
                confidence_score=0.0,
                error_message=f"AI provider error: {type(e).__name__}",
                is_ai_generated=True,
                requires_doctor_review=True,
            )

    @staticmethod
    def _build_prompt(request: ProcessIntakeRequest) -> str:
        return f"""You are a medical data extraction tool — NOT a doctor.
You do NOT diagnose. You do NOT prescribe. You do NOT give medical advice.
Your ONLY job is to extract structured information from patient intake notes.

Extract symptoms, possible conditions to investigate, and explicitly list
any information that is missing or unknown.

Return ONLY valid JSON matching this exact schema:
{{
  "symptoms": ["list of symptoms mentioned"],
  "potential_conditions": ["conditions to investigate — NOT diagnoses"],
  "unknown_information": ["information missing from the intake"]
}}

If the intake is empty or unintelligible, return empty lists and list
"Intake was empty or unintelligible" in unknown_information.

Patient intake notes:
{request.clinical_notes}
"""

    @staticmethod
    def _parse_response(raw_text: str) -> StructuredClinicalOutput:
        """Parse and validate Gemini's JSON response through Pydantic."""
        data = json.loads(raw_text)

        # Validate through Pydantic — field_validator in ClinicalAssessment
        # will coerce malformed types safely.
        assessment = ClinicalAssessment(
            symptoms=data.get("symptoms", []),
            potential_conditions=data.get("potential_conditions", []),
            unknown_information=data.get("unknown_information", []),
            source_traces={},
        )

        return StructuredClinicalOutput(
            status=AIOutputStatus.SUCCESS,
            # Confidence is NOT fabricated — we use a conservative default
            # since Gemini does not return a confidence score natively.
            confidence_score=0.0,
            assessment=assessment,
            is_ai_generated=True,
            requires_doctor_review=True,
        )

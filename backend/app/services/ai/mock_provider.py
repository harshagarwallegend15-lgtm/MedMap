from app.services.ai.provider import BaseAIProvider
from app.services.ai.schemas import (
    ProcessIntakeRequest,
    StructuredClinicalOutput,
    ClinicalAssessment,
    AIOutputStatus,
)


class MockProvider(BaseAIProvider):
    """Deterministic mock provider for development and testing.

    Returns a safe, hardcoded response. All output is explicitly
    marked as AI-generated and requiring doctor review.
    """

    def process_case(self, request: ProcessIntakeRequest) -> StructuredClinicalOutput:
        return StructuredClinicalOutput(
            status=AIOutputStatus.SUCCESS,
            confidence_score=0.5,
            assessment=ClinicalAssessment(
                symptoms=["Fever (Mock)", "Cough (Mock)"],
                potential_conditions=["Common Cold (Mock)"],
                unknown_information=[
                    "Duration of symptoms",
                    "Patient temperature",
                ],
                source_traces={},
            ),
            is_ai_generated=True,
            requires_doctor_review=True,
        )

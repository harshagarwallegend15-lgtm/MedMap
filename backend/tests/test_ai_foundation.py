import pytest
from unittest.mock import patch, MagicMock

from app.services.ai.processor import AIProcessor
from app.services.ai.mock_provider import MockProvider
from app.services.ai.schemas import (
    ProcessIntakeRequest,
    StructuredClinicalOutput,
    ClinicalAssessment,
    AIOutputStatus,
)
from app.services.ai.config import AIConfig


# ---------------------------------------------------------------------------
# Provider selection / fallback
# ---------------------------------------------------------------------------

def test_default_config_uses_mock():
    """Default AI_PROVIDER=mock should use MockProvider."""
    cfg = AIConfig.__new__(AIConfig)
    cfg.provider = "mock"
    cfg.gemini_api_key = None

    processor = AIProcessor(ai_config=cfg)
    assert isinstance(processor.provider, MockProvider)


def test_gemini_without_key_falls_back_to_mock():
    """If provider=gemini but no API key, must fall back to mock safely."""
    cfg = AIConfig.__new__(AIConfig)
    cfg.provider = "gemini"
    cfg.gemini_api_key = ""

    processor = AIProcessor(ai_config=cfg)
    assert isinstance(processor.provider, MockProvider)


# ---------------------------------------------------------------------------
# Mock provider determinism
# ---------------------------------------------------------------------------

def test_mock_provider_deterministic_output():
    provider = MockProvider()
    request = ProcessIntakeRequest(
        patient_id="test-123",
        clinical_notes="Patient has a fever.",
    )
    result = provider.process_case(request)

    assert result.status == AIOutputStatus.SUCCESS
    assert result.assessment is not None
    assert "Fever (Mock)" in result.assessment.symptoms
    assert "Patient temperature" in result.assessment.unknown_information
    assert result.is_ai_generated is True
    assert result.requires_doctor_review is True


# ---------------------------------------------------------------------------
# Safe failure
# ---------------------------------------------------------------------------

def test_processor_safe_failure_on_provider_exception():
    """If the provider raises, processor must return a safe failure object."""
    cfg = AIConfig.__new__(AIConfig)
    cfg.provider = "mock"
    cfg.gemini_api_key = None

    processor = AIProcessor(ai_config=cfg)
    # Replace the provider with one that always raises
    processor.provider = MagicMock(
        side_effect=ValueError("Simulated failure")
    )
    processor.provider.process_case = MagicMock(
        side_effect=ValueError("Simulated failure")
    )

    request = ProcessIntakeRequest(
        patient_id="test-456",
        clinical_notes="Headache.",
    )
    result = processor.process_intake(request)

    assert result.status == AIOutputStatus.FAILED
    assert result.error_message == "Internal processing error"
    assert result.assessment is None
    assert result.is_ai_generated is True
    assert result.requires_doctor_review is True


# ---------------------------------------------------------------------------
# Malformed / invalid structured output
# ---------------------------------------------------------------------------

def test_clinical_assessment_coerces_string_to_list():
    """If Gemini returns a string instead of a list, it must be safely coerced."""
    assessment = ClinicalAssessment(
        symptoms="just a string",
        potential_conditions=12345,  # completely wrong type
        unknown_information=None,
    )
    assert assessment.symptoms == ["just a string"]
    assert assessment.potential_conditions == []
    assert assessment.unknown_information == []


def test_structured_output_rejects_invalid_confidence():
    """Confidence must be between 0.0 and 1.0."""
    with pytest.raises(Exception):
        StructuredClinicalOutput(
            status=AIOutputStatus.SUCCESS,
            confidence_score=5.0,  # out of bounds
        )


def test_structured_output_rejects_invalid_status():
    """Status must be a valid AIOutputStatus value."""
    with pytest.raises(Exception):
        StructuredClinicalOutput(
            status="made_up_status",
            confidence_score=0.5,
        )


# ---------------------------------------------------------------------------
# Empty / edge-case input
# ---------------------------------------------------------------------------

def test_mock_provider_handles_empty_notes():
    """Mock provider should still return a safe result for empty input."""
    provider = MockProvider()
    request = ProcessIntakeRequest(
        patient_id="test-empty",
        clinical_notes="",
    )
    result = provider.process_case(request)
    assert result.status == AIOutputStatus.SUCCESS
    assert result.is_ai_generated is True


# ---------------------------------------------------------------------------
# Safety invariants
# ---------------------------------------------------------------------------

def test_processor_always_marks_output_as_ai_generated():
    """No matter what the provider returns, the processor must enforce
    is_ai_generated=True and requires_doctor_review=True."""
    cfg = AIConfig.__new__(AIConfig)
    cfg.provider = "mock"
    cfg.gemini_api_key = None

    processor = AIProcessor(ai_config=cfg)

    request = ProcessIntakeRequest(
        patient_id="test-safety",
        clinical_notes="Test notes",
    )
    result = processor.process_intake(request)

    assert result.is_ai_generated is True
    assert result.requires_doctor_review is True


# ---------------------------------------------------------------------------
# No coupling assertions
# ---------------------------------------------------------------------------

def test_no_database_imports():
    """The AI module must not import from database, models, or case modules."""
    import app.services.ai.processor as proc_mod
    import app.services.ai.schemas as schema_mod
    import app.services.ai.mock_provider as mock_mod
    import app.services.ai.config as config_mod

    for mod in [proc_mod, schema_mod, mock_mod, config_mod]:
        source_file = mod.__file__
        with open(source_file, "r") as f:
            content = f.read()
        assert "from app.models" not in content, f"{source_file} imports app.models"
        assert "from app.core.database" not in content, f"{source_file} imports database"
        assert "from app.api" not in content, f"{source_file} imports app.api"

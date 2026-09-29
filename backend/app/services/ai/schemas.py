from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from enum import Enum


class AIOutputStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ProcessIntakeRequest(BaseModel):
    patient_id: str
    clinical_notes: str


class SourceTrace(BaseModel):
    source: str
    extracted_text: str


class ClinicalAssessment(BaseModel):
    symptoms: List[str] = Field(
        default_factory=list,
        description="Extracted symptoms"
    )
    potential_conditions: List[str] = Field(
        default_factory=list,
        description="Possible conditions to investigate — NOT diagnoses"
    )
    unknown_information: List[str] = Field(
        default_factory=list,
        description="Information missing from the intake"
    )
    source_traces: Dict[str, SourceTrace] = Field(
        default_factory=dict,
        description="Traceability of extracted facts"
    )

    @field_validator("symptoms", "potential_conditions", "unknown_information", mode="before")
    @classmethod
    def coerce_to_list(cls, v):
        """Safely handle malformed model output where a string is returned instead of a list."""
        if isinstance(v, str):
            return [v] if v else []
        if not isinstance(v, list):
            return []
        return v


class StructuredClinicalOutput(BaseModel):
    status: AIOutputStatus = Field(
        ...,
        description="Status of the AI processing"
    )
    confidence_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence from 0.0 to 1.0"
    )
    assessment: Optional[ClinicalAssessment] = None
    error_message: Optional[str] = None
    is_ai_generated: bool = Field(
        default=True,
        description="Always True. AI output is NEVER a verified clinical fact."
    )
    requires_doctor_review: bool = Field(
        default=True,
        description="Always True. AI output must always be reviewed by a doctor."
    )

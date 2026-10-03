from enum import Enum
from typing import Optional, List, Union, Dict
from pydantic import BaseModel, Field


class ConditionOperator(str, Enum):
    """Supported deterministic condition operators."""
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    NOT_EMPTY = "NOT_EMPTY"
    CONTAINS = "CONTAINS"
    CONTAINS_ANY = "CONTAINS_ANY"
    ALWAYS = "ALWAYS"


class ConditionRule(BaseModel):
    """A deterministic prerequisite rule for question eligibility."""
    depends_on: str = Field(
        ...,
        description="ID of the prerequisite question whose answer is evaluated."
    )
    operator: ConditionOperator = Field(
        default=ConditionOperator.NOT_EMPTY,
        description="Operator applied to prerequisite question's answer."
    )
    value: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Expected value or target substrings for comparison."
    )

    def evaluate(self, answers: Dict[str, str]) -> bool:
        """Evaluate condition against current answers map.

        Deterministic rules:
        - ALWAYS returns True.
        - If prerequisite question is missing from answers, returns False.
        - An empty-string answer represents an explicitly skipped question.
        - Skipped prerequisite fails NOT_EMPTY, CONTAINS, and CONTAINS_ANY.
        - EQUALS and NOT_EQUALS evaluate literal equality.
        """
        if self.operator == ConditionOperator.ALWAYS:
            return True

        if self.depends_on not in answers:
            # Prerequisite question has not been resolved (unanswered)
            return False

        prereq_ans = answers[self.depends_on]
        prereq_stripped = prereq_ans.strip()

        if self.operator == ConditionOperator.NOT_EMPTY:
            # Must have non-empty text; empty string (skipped) evaluates to False
            return len(prereq_stripped) > 0

        if self.operator == ConditionOperator.EQUALS:
            target = "" if self.value is None else str(self.value).strip()
            return prereq_stripped.lower() == target.lower()

        if self.operator == ConditionOperator.NOT_EQUALS:
            target = "" if self.value is None else str(self.value).strip()
            return prereq_stripped.lower() != target.lower()

        if self.operator == ConditionOperator.CONTAINS:
            if not prereq_stripped or self.value is None:
                return False
            target = str(self.value).strip().lower()
            return target in prereq_stripped.lower()

        if self.operator == ConditionOperator.CONTAINS_ANY:
            if not prereq_stripped or self.value is None:
                return False
            if isinstance(self.value, list):
                targets = [str(v).strip().lower() for v in self.value if str(v).strip()]
            else:
                targets = [str(self.value).strip().lower()]
            return any(t in prereq_stripped.lower() for t in targets if t)

        return False


class QuestionDefinition(BaseModel):
    """Domain model representing a single intake question."""
    id: str = Field(..., description="Unique stable identifier (e.g. 'chief_complaint')")
    category: str = Field(..., description="Category or grouping name")
    prompt: str = Field(..., description="Question prompt presented to the patient")
    input_type: str = Field(default="textarea", description="'text' or 'textarea'")
    order: int = Field(default=0, description="Deterministic ordering index")
    conditions: Optional[List[ConditionRule]] = Field(
        default=None,
        description="Eligibility conditions. All conditions must be met (logical AND)."
    )


class EngineStatus(str, Enum):
    QUESTION = "question"
    COMPLETE = "complete"


class AdaptiveEngineResult(BaseModel):
    """Result of adaptive engine question selection."""
    status: EngineStatus = Field(..., description="'question' or 'complete'")
    next_question: Optional[QuestionDefinition] = Field(
        default=None,
        description="The next eligible question to ask, or None if complete."
    )
    is_complete: bool = Field(
        default=False,
        description="True when no eligible unanswered questions remain."
    )
    answered_count: int = Field(
        default=0,
        description="Number of answered questions (non-empty answers)."
    )
    skipped_count: int = Field(
        default=0,
        description="Number of skipped questions (empty answers)."
    )
    total_eligible_questions: int = Field(
        default=0,
        description="Total number of eligible questions based on current answers."
    )

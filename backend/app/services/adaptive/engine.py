from typing import Optional, List, Dict, Any
from app.services.adaptive.schemas import (
    QuestionDefinition,
    AdaptiveEngineResult,
    EngineStatus,
)
from app.services.adaptive.default_questions import DEFAULT_INTAKE_QUESTIONS


class AdaptiveIntakeEngine:
    """Pure deterministic Adaptive Question Engine for patient intake.

    Selects the next applicable unanswered question based on patient answers
    and deterministic question eligibility conditions.
    """

    def __init__(self, catalog: Optional[List[QuestionDefinition]] = None):
        """Initialize engine with question catalog.

        Explicit None check preserves an empty catalog list if provided:
        - catalog=None -> use DEFAULT_INTAKE_QUESTIONS
        - catalog=[] -> evaluate empty catalog (returns COMPLETE)
        """
        if catalog is None:
            self.catalog = list(DEFAULT_INTAKE_QUESTIONS)
        else:
            self.catalog = list(catalog)

    @staticmethod
    def _normalize_answers(answers: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Defensively normalize answers dictionary.

        - None is converted to empty dict.
        - Non-dict input is converted to empty dict.
        - Keys and values are converted to string. None value is treated as empty string.
        """
        if answers is None:
            return {}
        if not isinstance(answers, dict):
            return {}

        normalized: Dict[str, str] = {}
        for k, v in answers.items():
            key_str = str(k)
            if v is None:
                normalized[key_str] = ""
            elif isinstance(v, str):
                normalized[key_str] = v
            else:
                normalized[key_str] = str(v)
        return normalized

    def get_next_question(
        self,
        answers: Optional[Dict[str, Any]] = None
    ) -> AdaptiveEngineResult:
        """Determine the next applicable unanswered question.

        Selection algorithm:
        1. Normalize input answers.
        2. Sort question catalog deterministically by (order, id).
        3. For each question:
           - Check if resolved (present in answers as answered or skipped).
           - Check eligibility (all conditions satisfied; empty conditions = always eligible).
           - If eligible and unresolved, select the first one as next_question.
        4. If no eligible unanswered questions remain, return COMPLETE.
        """
        norm_answers = self._normalize_answers(answers)

        # Stable deterministic ordering: primary key = order, secondary tie-breaker = id
        sorted_questions = sorted(self.catalog, key=lambda q: (q.order, q.id))

        next_question: Optional[QuestionDefinition] = None
        answered_count = 0
        skipped_count = 0
        total_eligible_questions = 0

        for q in sorted_questions:
            is_resolved = q.id in norm_answers

            if is_resolved:
                if norm_answers[q.id].strip():
                    answered_count += 1
                else:
                    skipped_count += 1

            # Evaluate conditions (logical AND). No conditions means always eligible.
            if not q.conditions:
                is_eligible = True
            else:
                is_eligible = all(cond.evaluate(norm_answers) for cond in q.conditions)

            if is_eligible:
                total_eligible_questions += 1
                if not is_resolved and next_question is None:
                    next_question = q

        if next_question is not None:
            return AdaptiveEngineResult(
                status=EngineStatus.QUESTION,
                next_question=next_question,
                is_complete=False,
                answered_count=answered_count,
                skipped_count=skipped_count,
                total_eligible_questions=total_eligible_questions,
            )

        return AdaptiveEngineResult(
            status=EngineStatus.COMPLETE,
            next_question=None,
            is_complete=True,
            answered_count=answered_count,
            skipped_count=skipped_count,
            total_eligible_questions=total_eligible_questions,
        )

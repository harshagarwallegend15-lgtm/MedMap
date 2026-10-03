import pytest
from app.services.adaptive.engine import AdaptiveIntakeEngine
from app.services.adaptive.schemas import (
    QuestionDefinition,
    ConditionRule,
    ConditionOperator,
    EngineStatus,
)
from app.services.adaptive.default_questions import DEFAULT_INTAKE_QUESTIONS


# ---------------------------------------------------------------------------
# 1. Default Catalog Progression Tests
# ---------------------------------------------------------------------------

def test_empty_answers_returns_chief_complaint():
    """Empty intake must return the first question in default catalog."""
    engine = AdaptiveIntakeEngine()
    result = engine.get_next_question({})

    assert result.status == EngineStatus.QUESTION
    assert result.is_complete is False
    assert result.next_question is not None
    assert result.next_question.id == "chief_complaint"
    assert result.answered_count == 0
    assert result.skipped_count == 0


def test_answered_question_is_not_selected_again():
    """An answered question must be marked resolved and never selected again."""
    engine = AdaptiveIntakeEngine()
    result = engine.get_next_question({"chief_complaint": "Persistent headache"})

    assert result.status == EngineStatus.QUESTION
    assert result.is_complete is False
    assert result.next_question is not None
    assert result.next_question.id == "present_illness"
    assert result.answered_count == 1
    assert result.skipped_count == 0


def test_skipped_question_is_treated_as_resolved():
    """An empty-string answer represents an explicitly skipped question."""
    engine = AdaptiveIntakeEngine()
    result = engine.get_next_question({
        "chief_complaint": "",  # Skipped
    })

    assert result.status == EngineStatus.QUESTION
    assert result.is_complete is False
    assert result.next_question is not None
    assert result.next_question.id == "present_illness"
    assert result.answered_count == 0
    assert result.skipped_count == 1


# ---------------------------------------------------------------------------
# 2. Synthetic Conditional Logic Tests (Neutral, non-clinical)
# ---------------------------------------------------------------------------

def test_unanswered_dependent_question_remains_ineligible_when_prerequisite_missing():
    """A dependent question must not be selected if prerequisite answer is missing."""
    synthetic_catalog = [
        QuestionDefinition(
            id="screening",
            category="General",
            prompt="Do you have symptoms? (yes/no)",
            order=1,
        ),
        QuestionDefinition(
            id="details",
            category="General",
            prompt="Please provide details.",
            order=2,
            conditions=[
                ConditionRule(
                    depends_on="screening",
                    operator=ConditionOperator.EQUALS,
                    value="yes",
                )
            ],
        ),
        QuestionDefinition(
            id="closing",
            category="General",
            prompt="Any additional comments?",
            order=3,
        ),
    ]
    engine = AdaptiveIntakeEngine(catalog=synthetic_catalog)

    # When screening is not answered yet, screening is returned
    result1 = engine.get_next_question({})
    assert result1.next_question.id == "screening"

    # When screening is answered with 'no', 'details' is ineligible; 'closing' is selected
    result2 = engine.get_next_question({"screening": "no"})
    assert result2.status == EngineStatus.QUESTION
    assert result2.next_question.id == "closing"


def test_dependent_question_becomes_eligible_when_condition_satisfied():
    """A dependent question is selected when its prerequisite condition passes."""
    synthetic_catalog = [
        QuestionDefinition(
            id="screening",
            category="General",
            prompt="Do you have symptoms? (yes/no)",
            order=1,
        ),
        QuestionDefinition(
            id="details",
            category="General",
            prompt="Please provide details.",
            order=2,
            conditions=[
                ConditionRule(
                    depends_on="screening",
                    operator=ConditionOperator.EQUALS,
                    value="yes",
                )
            ],
        ),
    ]
    engine = AdaptiveIntakeEngine(catalog=synthetic_catalog)

    result = engine.get_next_question({"screening": "yes"})
    assert result.status == EngineStatus.QUESTION
    assert result.next_question is not None
    assert result.next_question.id == "details"


def test_multiple_conditions_use_and_semantics():
    """All conditions on a question must evaluate to True (logical AND)."""
    synthetic_catalog = [
        QuestionDefinition(id="q1", category="G", prompt="Q1", order=1),
        QuestionDefinition(id="q2", category="G", prompt="Q2", order=2),
        QuestionDefinition(
            id="q3",
            category="G",
            prompt="Q3",
            order=3,
            conditions=[
                ConditionRule(depends_on="q1", operator=ConditionOperator.EQUALS, value="A"),
                ConditionRule(depends_on="q2", operator=ConditionOperator.EQUALS, value="B"),
            ],
        ),
    ]
    engine = AdaptiveIntakeEngine(catalog=synthetic_catalog)

    # q1 matches but q2 does not -> q3 is ineligible -> complete
    result1 = engine.get_next_question({"q1": "A", "q2": "wrong"})
    assert result1.status == EngineStatus.COMPLETE
    assert result1.next_question is None

    # Both match -> q3 is eligible
    result2 = engine.get_next_question({"q1": "A", "q2": "B"})
    assert result2.status == EngineStatus.QUESTION
    assert result2.next_question.id == "q3"


def test_not_empty_does_not_pass_for_empty_string_skipped_answer():
    """An empty-string skipped answer must fail NOT_EMPTY operator."""
    cond = ConditionRule(
        depends_on="q1",
        operator=ConditionOperator.NOT_EMPTY,
    )
    # Missing answer -> False
    assert cond.evaluate({}) is False
    # Explicitly skipped (empty string) -> False
    assert cond.evaluate({"q1": ""}) is False
    # Whitespace only -> False
    assert cond.evaluate({"q1": "   "}) is False
    # Non-empty answer -> True
    assert cond.evaluate({"q1": "Some value"}) is True


def test_contains_and_contains_any_operators():
    """CONTAINS and CONTAINS_ANY evaluate substring matches safely."""
    cond_contains = ConditionRule(
        depends_on="q1",
        operator=ConditionOperator.CONTAINS,
        value="headache",
    )
    assert cond_contains.evaluate({"q1": "mild headache reported"}) is True
    assert cond_contains.evaluate({"q1": "fever only"}) is False
    assert cond_contains.evaluate({"q1": ""}) is False

    cond_any = ConditionRule(
        depends_on="q1",
        operator=ConditionOperator.CONTAINS_ANY,
        value=["cough", "fever"],
    )
    assert cond_any.evaluate({"q1": "patient has a fever"}) is True
    assert cond_any.evaluate({"q1": "patient has a dry cough"}) is True
    assert cond_any.evaluate({"q1": "patient has headache"}) is False
    assert cond_any.evaluate({"q1": ""}) is False


# ---------------------------------------------------------------------------
# 3. Completion & Boundary Tests
# ---------------------------------------------------------------------------

def test_completion_occurs_when_no_eligible_unanswered_questions_remain():
    """Intake completes when all eligible questions are answered or skipped."""
    engine = AdaptiveIntakeEngine()
    all_answers = {q.id: "recorded answer" for q in DEFAULT_INTAKE_QUESTIONS}

    result = engine.get_next_question(all_answers)
    assert result.status == EngineStatus.COMPLETE
    assert result.is_complete is True
    assert result.next_question is None
    assert result.answered_count == len(DEFAULT_INTAKE_QUESTIONS)


def test_completion_with_ineligible_questions():
    """Completion occurs even if an ineligible question was never answered."""
    synthetic_catalog = [
        QuestionDefinition(id="q1", category="G", prompt="Q1", order=1),
        QuestionDefinition(
            id="q2",
            category="G",
            prompt="Q2",
            order=2,
            conditions=[
                ConditionRule(depends_on="q1", operator=ConditionOperator.EQUALS, value="activate")
            ],
        ),
    ]
    engine = AdaptiveIntakeEngine(catalog=synthetic_catalog)

    # Patient skipped or answered differently -> q2 is ineligible -> completed
    result = engine.get_next_question({"q1": ""})
    assert result.status == EngineStatus.COMPLETE
    assert result.is_complete is True
    assert result.next_question is None


def test_empty_catalog_returns_complete():
    """Explicitly passing catalog=[] must evaluate to complete immediately."""
    engine = AdaptiveIntakeEngine(catalog=[])
    result = engine.get_next_question({})

    assert result.status == EngineStatus.COMPLETE
    assert result.is_complete is True
    assert result.next_question is None
    assert result.total_eligible_questions == 0


def test_malformed_and_none_answers_handled_safely():
    """Engine must normalize None, non-dict, and non-string values gracefully."""
    engine = AdaptiveIntakeEngine()

    # None answers
    res1 = engine.get_next_question(None)
    assert res1.status == EngineStatus.QUESTION
    assert res1.next_question.id == "chief_complaint"

    # Non-string answer values
    res2 = engine.get_next_question({"chief_complaint": 12345, "present_illness": None})
    assert res2.status == EngineStatus.QUESTION
    assert res2.next_question.id == "past_medical"
    assert res2.answered_count == 1  # 12345 coerced to string
    assert res2.skipped_count == 1   # None coerced to ""


def test_deterministic_repeated_evaluation_produces_identical_results():
    """Identical inputs must produce identical outputs on repeated execution."""
    engine = AdaptiveIntakeEngine()
    answers = {"chief_complaint": "headache", "present_illness": ""}

    first_run = engine.get_next_question(answers)
    for _ in range(50):
        run = engine.get_next_question(answers)
        assert run.status == first_run.status
        assert run.next_question.id == first_run.next_question.id
        assert run.is_complete == first_run.is_complete
        assert run.answered_count == first_run.answered_count
        assert run.skipped_count == first_run.skipped_count


def test_circular_dependency_terminates_safely():
    """Circular conditions between unanswered questions must not cause infinite loops."""
    circular_catalog = [
        QuestionDefinition(
            id="qA",
            category="G",
            prompt="QA",
            order=1,
            conditions=[ConditionRule(depends_on="qB", operator=ConditionOperator.NOT_EMPTY)],
        ),
        QuestionDefinition(
            id="qB",
            category="G",
            prompt="QB",
            order=2,
            conditions=[ConditionRule(depends_on="qA", operator=ConditionOperator.NOT_EMPTY)],
        ),
    ]
    engine = AdaptiveIntakeEngine(catalog=circular_catalog)
    # Neither can be satisfied -> both are ineligible -> completes safely in 1 pass
    result = engine.get_next_question({})
    assert result.status == EngineStatus.COMPLETE
    assert result.is_complete is True
    assert result.next_question is None


# ---------------------------------------------------------------------------
# 4. Architectural Decoupling Invariant
# ---------------------------------------------------------------------------

def test_no_database_or_network_dependency():
    """Adaptive service module must have zero coupling to database, models, or APIs."""
    import app.services.adaptive.engine as eng_mod
    import app.services.adaptive.schemas as schema_mod
    import app.services.adaptive.default_questions as dq_mod

    for mod in [eng_mod, schema_mod, dq_mod]:
        source_file = mod.__file__
        with open(source_file, "r") as f:
            content = f.read()
        assert "from app.models" not in content, f"{source_file} imports app.models"
        assert "from app.core.database" not in content, f"{source_file} imports database"
        assert "from app.api" not in content, f"{source_file} imports app.api"
        assert "requests" not in content, f"{source_file} imports requests"
        assert "urllib" not in content, f"{source_file} imports urllib"
        assert "httpx" not in content, f"{source_file} imports httpx"

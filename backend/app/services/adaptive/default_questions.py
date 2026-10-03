from typing import List
from app.services.adaptive.schemas import QuestionDefinition

# Canonical default intake questions matching existing frontend INTAKE_QUESTIONS
DEFAULT_INTAKE_QUESTIONS: List[QuestionDefinition] = [
    QuestionDefinition(
        id="chief_complaint",
        category="Chief Complaint",
        prompt="What is the main reason for your visit today?",
        input_type="text",
        order=1,
        conditions=None,
    ),
    QuestionDefinition(
        id="present_illness",
        category="History of Present Illness",
        prompt="Please describe your current symptoms in detail.",
        input_type="textarea",
        order=2,
        conditions=None,
    ),
    QuestionDefinition(
        id="past_medical",
        category="Past Medical History",
        prompt="Do you have any previously diagnosed medical conditions?",
        input_type="textarea",
        order=3,
        conditions=None,
    ),
    QuestionDefinition(
        id="past_surgical",
        category="Past Surgical History",
        prompt="Have you had any surgeries or procedures in the past?",
        input_type="textarea",
        order=4,
        conditions=None,
    ),
    QuestionDefinition(
        id="medications",
        category="Medication History",
        prompt="What medications are you currently taking?",
        input_type="textarea",
        order=5,
        conditions=None,
    ),
    QuestionDefinition(
        id="allergies",
        category="Allergies",
        prompt="Do you have any known allergies?",
        input_type="textarea",
        order=6,
        conditions=None,
    ),
    QuestionDefinition(
        id="family_history",
        category="Family History",
        prompt="Is there any significant medical history in your immediate family?",
        input_type="textarea",
        order=7,
        conditions=None,
    ),
    QuestionDefinition(
        id="review_of_systems",
        category="Review of Systems",
        prompt="Are you experiencing any other symptoms we haven't discussed?",
        input_type="textarea",
        order=8,
        conditions=None,
    ),
]

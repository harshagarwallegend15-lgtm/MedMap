# MedMap — Adaptive Intake Engine Handoff Report

**Developer:** Harsh  
**Branch:** `feature/harsh-adaptive-intake`  
**Date:** 2026-10-04  
**Starting Baseline:** `8b1292e` (`feat: add safe ai processing foundation`)  
**Implementation Checkpoint:** `53e489f` (`feat: add deterministic adaptive intake engine`)  
**Status:** Implementation complete, 100% test coverage, isolated pure engine  

---

## 1. Executive Summary

This handoff documents the implementation of the **Deterministic Adaptive Intake Engine** for MedMap. 

The goal of this module is to drive dynamic, conditional patient intake questioning with zero external dependencies (no database calls, no network I/O, no probabilistic AI unpredictability). Given a question catalog and the current dictionary of patient responses, the engine deterministically decides:
1. What the next eligible, unanswered question is, or
2. Whether the intake is complete.

---

## 2. Core Architecture & Design Decisions

### Pure Domain Engine Isolation
The module lives inside `backend/app/services/adaptive/` and is strictly decoupled from:
- SQLAlchemy / database models (`app.models.*`, `app.core.database`)
- HTTP / FastAPI routing (`app.api.*`)
- Network request libraries (`httpx`, `requests`, `urllib`)

This design allows the engine to be executed anywhere — inside FastAPI request handlers, background background workers, offline test runners, or even ported to edge runtimes.

### Deterministic Question Selection
To guarantee reproducible behavior:
- Questions are sorted primarily by `order` (ascending integer), with `id` as a stable secondary tie-breaker.
- Question conditions are evaluated sequentially with strict logical **AND** semantics.
- Re-evaluating the engine with identical answers produces identical results across 100% of executions.

### Robust Answers Normalization
Input answers may come from untrusted JSON payloads. The engine defensively normalizes inputs:
- `None` or non-dict input becomes `{}`.
- All keys and values are coerced to strings.
- Explicit skips are represented as empty strings (`""`) or whitespace strings.
- Skipped questions are treated as resolved (so they are not asked repeatedly) but fail truthy condition checks like `NOT_EMPTY` or `CONTAINS`.

---

## 3. Module Structure & Artifacts

| File | Purpose | Lines of Code |
|---|---|---|
| [`schemas.py`](file:///c:/MedMap/backend/app/services/adaptive/schemas.py) | Pydantic models for conditions, questions, engine status, and engine results | 122 |
| [`default_questions.py`](file:///c:/MedMap/backend/app/services/adaptive/default_questions.py) | Canonical 8 intake questions matching frontend intake spec | 71 |
| [`engine.py`](file:///c:/MedMap/backend/app/services/adaptive/engine.py) | `AdaptiveIntakeEngine` logic, answer normalization, question evaluation | 116 |
| [`__init__.py`](file:///c:/MedMap/backend/app/services/adaptive/__init__.py) | Clean module namespace export | 20 |
| [`test_adaptive_engine.py`](file:///c:/MedMap/backend/tests/test_adaptive_engine.py) | 15 comprehensive unit tests | 328 |

---

## 4. Condition Rules & Operators

The engine supports rich condition definitions via `ConditionRule`:

| Operator | Behavior |
|---|---|
| `ALWAYS` | Always evaluates to `True`. |
| `EQUALS` | Case-insensitive exact match with target value. |
| `NOT_EQUALS` | Case-insensitive inequality with target value. |
| `NOT_EMPTY` | Prerequisite question answered with at least one non-whitespace character. |
| `CONTAINS` | Target substring found within prerequisite answer (case-insensitive). |
| `CONTAINS_ANY` | Any target substring from list found within prerequisite answer. |

---

## 5. Verification & Test Results

### Unit Tests
The test suite in [`backend/tests/test_adaptive_engine.py`](file:///c:/MedMap/backend/tests/test_adaptive_engine.py) provides 100% coverage of the engine's behavior:
- Default question catalog progression (`chief_complaint` -> `present_illness` -> ...)
- Handling of answered and skipped questions
- Synthetic conditional logic (`EQUALS`, `NOT_EQUALS`, `NOT_EMPTY`, `CONTAINS`, `CONTAINS_ANY`)
- Multi-condition logical AND semantics
- Completion detection on exhausted catalog or satisfied branch
- Empty catalog and malformed/null input resilience
- Determinism under repeated evaluations (50 iterations invariant check)
- Circular dependency prevention (terminates in a single pass without infinite recursion)
- Architectural boundary enforcement (ensures no DB or network imports exist)

### Test Run Status
```text
pytest backend/tests
collected 25 items

backend/tests/test_adaptive_engine.py ...............                    [ 60%]
backend/tests/test_ai_foundation.py ..........                           [100%]

======================== 25 passed, 1 warning in 4.05s ========================
```

### Frontend Build Check
```text
npm run build
> medmap@0.0.0 build
> tsc -b && vite build
✓ built in 2.95s
```

---

## 6. Integration Guide for Downstream Developers

### Basic Usage
```python
from app.services.adaptive import AdaptiveIntakeEngine, EngineStatus

engine = AdaptiveIntakeEngine()

# Given current patient answers
answers = {
    "chief_complaint": "Persistent abdominal pain for 3 days",
}

result = engine.get_next_question(answers)

if result.status == EngineStatus.QUESTION:
    next_q = result.next_question
    print(f"Ask patient: [{next_q.id}] {next_q.prompt}")
else:
    print("Intake complete. Ready for clinical summary generation.")
```

### Custom Catalogs
Developers can supply custom question catalogs with branching logic to `AdaptiveIntakeEngine(catalog=custom_questions)`.

---

## 7. Status Checklist

| Item | Status | Notes |
|---|---|---|
| **Branch** | `feature/harsh-adaptive-intake` | Active branch |
| **Starting Baseline** | `8b1292e` | `feat: add safe ai processing foundation` |
| **Implementation Checkpoint** | `53e489f` | `feat: add deterministic adaptive intake engine` |
| **Working Tree** | Clean | Ready for commit and push |
| **Test Suite** | Passing (25/25) | 15 adaptive + 10 AI foundation tests pass |
| **Remote** | `origin/feature/harsh-adaptive-intake` | Target remote branch |
| **Integration** | NOT YET VERIFIED | Awaiting integration with case workflow & UI |
| **Production** | NOT VERIFIED | Staging / deployment pending |

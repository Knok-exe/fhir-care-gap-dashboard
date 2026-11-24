from datetime import datetime, timezone

import pytest
from fhir_timeline.timeline import Event

from fhir_care_gaps.rules import DEFAULT_RULES, evaluate, evaluate_rule

AS_OF = datetime(2026, 11, 24, tzinfo=timezone.utc)
DIABETES, HTN, FLU = DEFAULT_RULES


def ev(kind, code, when, value="", system="LOINC", display=""):
    dt = datetime.fromisoformat(when).replace(tzinfo=timezone.utc) if when else None
    return Event(dt, kind, system, code, display or code, value, "", f"{kind}-{code}-{when}")


def cond(code, status="active", when="2019-01-01"):
    return ev("Condition", code, when, status, "SNOMED")


def hba1c(when):
    return ev("Observation", "4548-4", when, "7.2 %")


def status(rule, events, as_of=AS_OF):
    return evaluate_rule(rule, events, as_of).status


# ---- diabetes / HbA1c -------------------------------------------------------------------

def test_diabetic_with_recent_hba1c_is_ok():
    assert status(DIABETES, [cond("44054006"), hba1c("2026-08-01")]) == "ok"


def test_diabetic_with_old_hba1c_is_a_gap_and_shows_last_date():
    result = evaluate_rule(DIABETES, [cond("44054006"), hba1c("2025-01-10")], AS_OF)
    assert result.status == "gap"
    assert "2025-01-10" in result.detail
    assert any(e.code == "4548-4" for e in result.evidence)  # last result shown as evidence
    assert any(e.code == "44054006" for e in result.evidence)  # why the rule applied


def test_diabetic_with_no_hba1c_at_all_is_a_gap():
    result = evaluate_rule(DIABETES, [cond("44054006")], AS_OF)
    assert result.status == "gap" and "No qualifying result" in result.detail


def test_window_boundary_is_inclusive():
    exactly_180_days_ago = "2026-05-28"
    assert status(DIABETES, [cond("44054006"), hba1c(exactly_180_days_ago)]) == "ok"
    assert status(DIABETES, [cond("44054006"), hba1c("2026-05-27")]) == "gap"


def test_no_diabetes_means_not_applicable_even_with_no_hba1c():
    assert status(DIABETES, []) == "not_applicable"


def test_resolved_diabetes_is_not_applicable():
    assert status(DIABETES, [cond("44054006", "resolved")]) == "not_applicable"


# ---- missing data is not a gap ------------------------------------------------------------

def test_condition_without_status_is_unknown_not_gap():
    assert status(DIABETES, [cond("44054006", status="")]) == "unknown"


def test_undated_result_is_unknown_not_gap():
    undated = ev("Observation", "4548-4", None, "7.0 %")
    assert status(DIABETES, [cond("44054006"), undated]) == "unknown"


def test_future_dated_result_does_not_count():
    assert status(DIABETES, [cond("44054006"), hba1c("2027-01-01")]) == "gap"


# ---- hypertension / BP --------------------------------------------------------------------

def test_hypertension_recent_bp_ok_and_old_bp_gap():
    bp_recent = ev("Observation", "85354-9", "2026-10-01", "120/80 mmHg")
    bp_old = ev("Observation", "85354-9", "2026-05-01", "120/80 mmHg")
    assert status(HTN, [cond("59621000"), bp_recent]) == "ok"
    assert status(HTN, [cond("59621000"), bp_old]) == "gap"


# ---- influenza (applies to everyone) ----------------------------------------------------

def test_flu_vaccine_gap_for_everyone_without_condition():
    assert status(FLU, []) == "gap"


def test_flu_vaccine_ok_with_cvx_140():
    shot = ev("Immunization", "140", "2026-10-05", "completed", "CVX")
    assert status(FLU, [shot]) == "ok"


def test_non_flu_vaccine_does_not_satisfy_rule():
    other = ev("Immunization", "208", "2026-10-05", "completed", "CVX")
    assert status(FLU, [other]) == "gap"


# ---- whole-engine ------------------------------------------------------------------------

@pytest.mark.parametrize("events", [[], [cond("44054006")]])
def test_evaluate_returns_one_result_per_rule(events):
    results = evaluate(events, AS_OF)
    assert [r.rule.id for r in results] == [r.id for r in DEFAULT_RULES]
    assert all(r.as_of == AS_OF for r in results)

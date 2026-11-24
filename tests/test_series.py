from datetime import date, datetime, timezone

from fhir_timeline.timeline import Event

from fhir_care_gaps.series import BLOOD_PRESSURE, HBA1C, active_problems, bp_series, numeric_series


def ev(kind, code, when, value=""):
    dt = datetime.fromisoformat(when).replace(tzinfo=timezone.utc) if when else None
    return Event(dt, kind, "LOINC", code, code, value, "", "id")


def test_numeric_series_sorted_and_skips_undated_or_non_numeric():
    events = [ev("Observation", "4548-4", "2024-01-15", "7.2 %"),
              ev("Observation", "4548-4", "2023-07-20", "8.1 %"),
              ev("Observation", "4548-4", None, "6.0 %"),
              ev("Observation", "4548-4", "2025-01-01", "pending")]
    assert numeric_series(events, HBA1C) == [(date(2023, 7, 20), 8.1), (date(2024, 1, 15), 7.2)]


def test_bp_series_parses_systolic_and_diastolic():
    events = [ev("Observation", "85354-9", "2024-01-15", "142/88 mmHg")]
    assert bp_series(events) == [(date(2024, 1, 15), 142.0, 88.0)]
    assert BLOOD_PRESSURE[0] == "85354-9"


def test_active_problems_excludes_resolved():
    events = [ev("Condition", "1", "2020-01-01", "active"),
              ev("Condition", "2", "2020-01-01", "resolved")]
    assert [e.code for e in active_problems(events)] == ["1"]

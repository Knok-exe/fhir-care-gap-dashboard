from datetime import datetime, timezone

from fhir_timeline.cli import load_demo_resources
from fhir_timeline.timeline import build_timeline

from fhir_care_gaps.rules import evaluate
from fhir_care_gaps.view import events_frame, gap_counts, vitals_frames


def demo_events():
    return build_timeline(r for r in load_demo_resources() if r["resourceType"] != "Patient")


def at(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def test_demo_patient_shows_all_three_gaps_today():
    counts = gap_counts(evaluate(demo_events(), at(2026, 11, 24)))
    assert counts["gap"] == 3


def test_demo_patient_is_ok_when_evaluated_shortly_after_the_visit():
    counts = gap_counts(evaluate(demo_events(), at(2024, 3, 1)))
    assert counts["ok"] == 3 and counts["gap"] == 0


def test_demo_patient_gives_a_mixed_picture_in_mid_2024():
    results = {r.rule.id: r.status for r in evaluate(demo_events(), at(2024, 6, 1))}
    assert results["hypertension-bp-3mo"] == "gap"       # 138 days since 2024-01-15
    assert results["diabetes-hba1c-6mo"] == "ok"
    assert results["influenza-vaccine-12mo"] == "ok"


def test_events_frame_and_vitals_frames_shapes():
    frame = events_frame(demo_events())
    assert list(frame.columns) == ["Date", "Type", "Code", "Description", "Value", "Flag"]
    assert len(frame) == 10
    frames = vitals_frames(demo_events())
    assert list(frames["HbA1c (%)"]["HbA1c"]) == [8.1, 7.2]
    bp = frames["Blood pressure (mmHg)"]
    assert list(bp.columns) == ["Systolic", "Diastolic"] and bp.iloc[0].tolist() == [142.0, 88.0]
    assert frames["Weight (kg)"].empty

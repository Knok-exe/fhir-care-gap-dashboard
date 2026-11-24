"""Pure helpers that shape data for display (no Streamlit imports, so they are testable)."""

from __future__ import annotations

from collections import Counter

import pandas as pd
from fhir_timeline.timeline import Event

from .rules import RuleResult
from .series import BLOOD_PRESSURE, BMI, HBA1C, WEIGHT, bp_series, numeric_series

STATUS_LABEL = {"gap": "Gap", "ok": "OK", "unknown": "Unknown", "not_applicable": "Not applicable"}


def events_frame(events: list[Event]) -> pd.DataFrame:
    rows = [{"Date": e.date_str, "Type": e.kind, "Code": f"{e.code_system} {e.code}".strip(),
             "Description": e.display, "Value": e.value, "Flag": e.flag} for e in events]
    return pd.DataFrame(rows, columns=["Date", "Type", "Code", "Description", "Value", "Flag"])


def simple_frame(events: list[Event], columns: tuple[str, ...] = ("Date", "Description",
                                                                   "Status")) -> pd.DataFrame:
    rows = [{"Date": e.date_str, "Description": e.display, "Status": e.value} for e in events]
    return pd.DataFrame(rows, columns=list(columns))


def line_frame(points: list[tuple], columns: list[str]) -> pd.DataFrame:
    """points: [(date, v1[, v2])] -> DataFrame indexed by date for st.line_chart."""
    if not points:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(points, columns=["date"] + columns)
    return frame.set_index("date")


def vitals_frames(events: list[Event]) -> dict[str, pd.DataFrame]:
    return {
        "HbA1c (%)": line_frame(numeric_series(events, HBA1C), ["HbA1c"]),
        "Weight (kg)": line_frame(numeric_series(events, WEIGHT), ["Weight"]),
        "BMI (kg/m2)": line_frame(numeric_series(events, BMI), ["BMI"]),
        "Blood pressure (mmHg)": line_frame(bp_series(events), ["Systolic", "Diastolic"]),
    }


def gap_counts(results: list[RuleResult]) -> Counter:
    return Counter(r.status for r in results)


def result_title(result: RuleResult) -> str:
    return f"{STATUS_LABEL[result.status]}: {result.rule.name}"


__all__ = [
    "BLOOD_PRESSURE",
    "events_frame",
    "gap_counts",
    "line_frame",
    "result_title",
    "simple_frame",
    "vitals_frames",
]

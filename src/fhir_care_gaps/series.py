"""Turn timeline events into chartable numeric series and simple summary lists."""

from __future__ import annotations

import re
from datetime import date

from fhir_timeline.timeline import Event

# Percent (NGSP) HbA1c codes only. 59261-8 is the IFCC result in mmol/mol: it still counts for
# the care-gap rule, but plotting it on a % chart would mix units (53 mmol/mol is ~7 %).
HBA1C = ("4548-4", "17856-6", "4549-2")
WEIGHT = ("29463-7",)
BMI = ("39156-5",)
BLOOD_PRESSURE = ("85354-9", "55284-4")

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers(text: str) -> list[float]:
    return [float(n) for n in _NUMBER.findall(text or "")]


def _unit(text: str) -> str:
    return _NUMBER.sub("", text or "").strip()


def numeric_series(events: list[Event], codes: tuple[str, ...],
                   units: tuple[str, ...] | None = None) -> list[tuple[date, float]]:
    """(date, value) for dated Observations with one of the codes, oldest first.

    If `units` is given, values that carry a different unit are skipped rather than plotted on
    the wrong scale (e.g. weight in lb on a kg chart). Values with no unit are kept.
    """
    out = []
    for e in events:
        if e.kind != "Observation" or e.code not in codes or e.when is None:
            continue
        unit = _unit(e.value)
        if units is not None and unit and unit not in units:
            continue
        nums = _numbers(e.value)
        if nums:
            out.append((e.when.date(), nums[0]))
    return sorted(out)


def bp_series(events: list[Event]) -> list[tuple[date, float, float]]:
    """(date, systolic, diastolic) from values like '142/88 mmHg'."""
    out = []
    for e in events:
        if e.kind != "Observation" or e.code not in BLOOD_PRESSURE or e.when is None:
            continue
        nums = _numbers(e.value)
        if len(nums) >= 2:
            out.append((e.when.date(), nums[0], nums[1]))
    return sorted(out)


def active_problems(events: list[Event]) -> list[Event]:
    return [e for e in events if e.kind == "Condition" and e.value in {"active", "recurrence",
                                                                        "relapse"}]


def medications(events: list[Event]) -> list[Event]:
    return [e for e in events if e.kind == "MedicationRequest"]


def allergies(events: list[Event]) -> list[Event]:
    return [e for e in events if e.kind == "AllergyIntolerance"]

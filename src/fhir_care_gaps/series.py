"""Turn timeline events into chartable numeric series and simple summary lists."""

from __future__ import annotations

import re
from datetime import date

from fhir_timeline.timeline import Event

HBA1C = ("4548-4", "17856-6", "4549-2", "59261-8")
WEIGHT = ("29463-7",)
BMI = ("39156-5",)
BLOOD_PRESSURE = ("85354-9", "55284-4")

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers(text: str) -> list[float]:
    return [float(n) for n in _NUMBER.findall(text or "")]


def numeric_series(events: list[Event], codes: tuple[str, ...]) -> list[tuple[date, float]]:
    """(date, value) for dated Observations with one of the codes, oldest first."""
    out = []
    for e in events:
        if e.kind != "Observation" or e.code not in codes or e.when is None:
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

"""Care-gap rules: declarative definitions plus an evaluator that always shows its evidence.

A rule says: "if the patient has condition X (or everyone), a qualifying result of kind K with
one of codes C must exist within the last N days."

Statuses
    ok              a qualifying, dated result exists inside the window
    gap             the rule applies and no qualifying result exists inside the window
    not_applicable  the patient does not have the triggering condition
    unknown         we cannot tell (condition status missing, or the only results are undated)

Missing data is never silently a gap: if the evidence is ambiguous the status is ``unknown``.
Educational demo logic on synthetic data only. Not clinical decision support.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from fhir_timeline.timeline import Event

ACTIVE_STATUSES = {"active", "recurrence", "relapse"}

# Resource statuses that mean "this did not happen". A refused or mistaken immunization must not
# close a gap. (Observation events don't carry their status through the timeline, so only
# kinds whose Event.value *is* the status can be screened here.)
NOT_DONE_STATUSES = {"not-done", "entered-in-error"}
STATUS_IN_VALUE = {"Immunization", "MedicationRequest"}

# SNOMED CT concepts for the triggering conditions (small, documented subsets).
DIABETES_CODES = frozenset({"44054006", "46635009", "73211009"})
HYPERTENSION_CODES = frozenset({"59621000", "38341003"})

# LOINC concepts for the qualifying results.
HBA1C_CODES = frozenset({"4548-4", "17856-6", "4549-2", "59261-8"})
BLOOD_PRESSURE_CODES = frozenset({"85354-9", "55284-4", "8480-6", "8462-4"})

# CVX codes for seasonal influenza vaccines (subset; see docs/rules.md).
FLU_CVX_CODES = frozenset({"88", "140", "141", "150", "153", "155", "158", "161", "166", "168",
                           "171", "185", "186", "197", "205"})


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    explanation: str
    result_kind: str                      # Observation or Immunization
    result_codes: frozenset[str]
    window_days: int
    condition_codes: frozenset[str] = frozenset()   # empty = applies to every patient


@dataclass(frozen=True)
class RuleResult:
    rule: Rule
    status: str
    detail: str
    evidence: tuple[Event, ...] = ()
    as_of: datetime | None = None


DEFAULT_RULES: tuple[Rule, ...] = (
    Rule(
        id="diabetes-hba1c-6mo",
        name="Diabetes: HbA1c in the last 6 months",
        explanation="Patients with diabetes should have HbA1c checked at least every 6 months "
                    "(demo threshold).",
        result_kind="Observation",
        result_codes=HBA1C_CODES,
        window_days=180,
        condition_codes=DIABETES_CODES,
    ),
    Rule(
        id="hypertension-bp-3mo",
        name="Hypertension: blood pressure in the last 3 months",
        explanation="Patients with hypertension should have a recorded blood pressure at "
                    "least every 3 months (demo threshold).",
        result_kind="Observation",
        result_codes=BLOOD_PRESSURE_CODES,
        window_days=90,
        condition_codes=HYPERTENSION_CODES,
    ),
    Rule(
        id="influenza-vaccine-12mo",
        name="Influenza vaccine in the last 12 months",
        explanation="Everyone should have a seasonal influenza vaccine recorded each year "
                    "(demo threshold).",
        result_kind="Immunization",
        result_codes=FLU_CVX_CODES,
        window_days=365,
    ),
)


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _fmt(e: Event) -> str:
    return f"{e.date_str} {e.display or e.code}"


def evaluate_rule(rule: Rule, events: list[Event], as_of: datetime) -> RuleResult:
    as_of = _utc(as_of)
    trigger: list[Event] = []

    if rule.condition_codes:
        matches = [e for e in events if e.kind == "Condition" and e.code in rule.condition_codes]
        active = [e for e in matches if e.value in ACTIVE_STATUSES]
        no_status = [e for e in matches if not e.value]
        if active:
            trigger = active
        elif no_status:
            return RuleResult(rule, "unknown",
                              "Condition found but its clinical status is missing, so "
                              "applicability can't be confirmed.",
                              tuple(no_status), as_of)
        else:
            return RuleResult(rule, "not_applicable",
                              "No active matching condition on record.", (), as_of)

    matching = [e for e in events if e.kind == rule.result_kind and e.code in rule.result_codes]
    not_done = [e for e in matching
                if e.kind in STATUS_IN_VALUE and e.value in NOT_DONE_STATUSES]
    qualifying = [e for e in matching if e not in not_done]
    note = (f" ({len(not_done)} matching record(s) marked not done or entered in error were "
            "ignored.)" if not_done else "")
    cutoff = as_of - timedelta(days=rule.window_days)
    dated = sorted((e for e in qualifying if e.when and e.when <= as_of), key=lambda e: e.when)
    undated = [e for e in qualifying if e.when is None]
    recent = [e for e in dated if e.when >= cutoff]

    if recent:
        latest = recent[-1]
        return RuleResult(rule, "ok",
                          f"Last done {latest.date_str}, within {rule.window_days} days.",
                          tuple(trigger) + (latest,), as_of)
    if undated:
        return RuleResult(rule, "unknown",
                          "Matching results exist but have no date, so recency can't be "
                          "checked.", tuple(trigger) + tuple(undated), as_of)
    if dated:
        last = dated[-1]
        days = (as_of - last.when).days
        return RuleResult(rule, "gap",
                          f"Last done {last.date_str} ({days} days ago); window is "
                          f"{rule.window_days} days.{note}", tuple(trigger) + (last,), as_of)
    return RuleResult(rule, "gap",
                      f"No qualifying result on record; window is {rule.window_days} days."
                      f"{note}", tuple(trigger) + tuple(not_done), as_of)


def end_of_day(day: date) -> datetime:
    """Last instant of a calendar day (UTC), so results recorded on the as-of day count."""
    return datetime.combine(day, time.max, tzinfo=timezone.utc)


def evaluate(events: list[Event], as_of: datetime | None = None,
             rules: tuple[Rule, ...] = DEFAULT_RULES) -> list[RuleResult]:
    """Evaluate every rule against a patient's events as of a date (default: now, UTC)."""
    as_of = as_of or datetime.now(timezone.utc)
    return [evaluate_rule(r, events, as_of) for r in rules]


def describe_evidence(result: RuleResult) -> list[str]:
    """Plain-English evidence lines for display."""
    return [_fmt(e) for e in result.evidence]

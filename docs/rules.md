# Care-gap rules

> Educational demo logic on synthetic data. Not clinical decision support. Thresholds are
> illustrative, not guideline-accurate. Review any real use with a clinician.

A rule says: *if the patient has condition X (or everyone), a qualifying result must exist in the
last N days.* Rules live in `src/fhir_care_gaps/rules.py` as plain data.

| Rule id | Applies when | Needs a result of | Window |
|---|---|---|---|
| `diabetes-hba1c-6mo` | active diabetes (SNOMED 44054006, 46635009, 73211009) | HbA1c, LOINC 4548-4, 17856-6, 4549-2, 59261-8 | 180 days |
| `hypertension-bp-3mo` | active hypertension (SNOMED 59621000, 38341003) | Blood pressure, LOINC 85354-9, 55284-4, 8480-6, 8462-4 | 90 days |
| `influenza-vaccine-12mo` | everyone | Influenza vaccine, CVX 88, 140, 141, 150, 153, 155, 158, 161, 166, 168, 171, 185, 186, 197, 205 | 365 days |

## Statuses

| Status | Meaning |
|---|---|
| `ok` | A qualifying, dated result exists inside the window (window is inclusive). |
| `gap` | The rule applies and no qualifying result exists inside the window. |
| `not_applicable` | No active matching condition (resolved or absent). |
| `unknown` | Can't tell: the condition's status is missing, or the only results are undated. |

## Design decisions

- **Missing data is not a gap.** A condition with no clinical status, or results with no date,
  produce `unknown`, never a silent `gap`. (Tests: `test_condition_without_status_is_unknown_not_gap`,
  `test_undated_result_is_unknown_not_gap`.)
- **Future-dated results don't count.** A result dated after the evaluation date is ignored.
  The evaluation date is inclusive: anything recorded on that day, at any time, counts.
- **"Not done" is not done.** An immunization (or medication request) with status `not-done`
  or `entered-in-error` never satisfies a rule. It is listed as evidence so you can see it was
  ignored.
- **Every flag shows its evidence:** the triggering condition, the most recent qualifying result,
  and the rule's explanation.
- **The evaluation date is an input** (sidebar "as of"), which makes results reproducible and lets
  you see how a patient's status changes over time.

## Limitations

- Code lists are small subsets, not full value sets.
- No age, sex, pregnancy or exclusion logic. No medication-based triggers.
- Condition status comes from `clinicalStatus` only; `verificationStatus` is ignored.
- Observation status (e.g. `cancelled`) is not checked, because the shared timeline `Event`
  does not carry it.

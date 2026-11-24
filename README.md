# fhir-care-gap-dashboard

Streamlit dashboard over a FHIR R4 server: pick a **synthetic** patient, chart vitals over time
(HbA1c, blood pressure, weight, BMI), list problems / meds / allergies, and compute **care gaps**
with the rule, window and dated evidence shown next to every flag.

> **Synthetic test data only.** Educational demo rules, not clinical decision support, not a
> medical device. Never point this at real patient data.

Built on the client from [fhir-timeline-cli](https://github.com/Knok-exe/fhir-timeline-cli).

## Quick start

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"
fhir-care-gaps                      # opens the dashboard in your browser
```

Start with **Demo patient (offline)** in the sidebar. Then try the **"Evaluate care gaps as of"**
date: today shows 3 gaps; `2024-03-01` shows all OK; `2024-06-01` is mixed (blood pressure
overdue). Switch the source to **FHIR server** to search SondaHub's synthetic patients.

## What it demonstrates

- A small, declarative rules engine (`rules.py`) with statuses `ok / gap / not_applicable / unknown`
- **Missing data is not a gap**: ambiguous cases are `unknown`, each covered by a test
- Evidence-first UI: rule, window, triggering condition, last qualifying result
- Pure, tested data-shaping code (`series.py`, `view.py`) behind a thin Streamlit page (`app.py`)
- Reuse of a tested FHIR client (`$everything` with fallback, pagination, retry)

See [docs/rules.md](docs/rules.md) for every rule, code list and design decision.

## Layout

```
src/fhir_care_gaps/   rules.py  series.py  view.py  app.py  launch.py
tests/                rules, series, view/demo
docs/rules.md         rule definitions and limitations
```

## Limitations / next steps

- Small code subsets and illustrative thresholds, no age/sex/exclusion logic
- Charts use Streamlit's built-in line chart; Plotly would add hover and reference bands
- Live demo deployment (Streamlit Community Cloud) not set up yet

## License

MIT, see [LICENSE](LICENSE).

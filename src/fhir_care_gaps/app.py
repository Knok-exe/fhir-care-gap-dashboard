"""Streamlit app. Run with:  fhir-care-gaps   (or: streamlit run src/fhir_care_gaps/app.py)

SYNTHETIC TEST DATA ONLY. Educational demo logic, not clinical decision support.
"""

from __future__ import annotations

from datetime import datetime, time, timezone

import requests
import streamlit as st
from fhir_timeline.cli import fetch_resources, load_demo_resources, patient_label
from fhir_timeline.client import DEFAULT_SERVER, FhirClient, FhirError
from fhir_timeline.timeline import build_timeline

from fhir_care_gaps.rules import describe_evidence, evaluate
from fhir_care_gaps.series import active_problems, allergies, medications
from fhir_care_gaps.view import events_frame, gap_counts, result_title, simple_frame, vitals_frames

st.set_page_config(page_title="FHIR Care-Gap Dashboard", layout="wide")
st.title("FHIR Care-Gap & Vitals Dashboard")
st.warning("Synthetic test data only. Educational demo rules, not clinical decision support "
           "and not a medical device.")


@st.cache_data(ttl=300, show_spinner="Searching patients...")
def search_patients(server: str, name: str) -> list[dict]:
    return FhirClient(server).find_patients(name)


@st.cache_data(ttl=300, show_spinner="Loading patient record...")
def load_patient(server: str, patient_id: str, use_everything: bool) -> tuple[dict, list[dict]]:
    client = FhirClient(server)
    return client.read("Patient", patient_id), fetch_resources(client, patient_id, None,
                                                               use_everything)


def load_demo() -> tuple[dict, list[dict]]:
    resources = load_demo_resources()
    patient = next(r for r in resources if r["resourceType"] == "Patient")
    return patient, [r for r in resources if r["resourceType"] != "Patient"]


# ---------------- sidebar ----------------
with st.sidebar:
    st.header("Data source")
    source = st.radio("Source", ["Demo patient (offline)", "FHIR server"], index=0)
    as_of_date = st.date_input("Evaluate care gaps as of", value=datetime.now(timezone.utc).date())
    patient = None
    resources: list[dict] = []
    error = None

    if source.startswith("FHIR"):
        server = st.text_input("FHIR base URL", DEFAULT_SERVER)
        name = st.text_input("Search patients by name", "Smith")
        use_everything = st.checkbox("Use Patient/$everything", value=True)
        try:
            matches = search_patients(server, name) if name else []
            options = {patient_label(m): m["id"] for m in matches}
            manual_id = st.text_input("...or enter a patient id", "")
            chosen = st.selectbox("Matching patients", list(options)) if options else None
            patient_id = manual_id or (options[chosen] if chosen else "")
            if patient_id:
                patient, resources = load_patient(server, patient_id, use_everything)
        except (FhirError, requests.exceptions.RequestException) as exc:
            error = str(exc)
    else:
        patient, resources = load_demo()

if error:
    st.error(f"Could not load data: {error}")
    st.stop()
if patient is None:
    st.info("Pick a patient in the sidebar to begin.")
    st.stop()

events = build_timeline(resources)
as_of = datetime.combine(as_of_date, time.min, tzinfo=timezone.utc)
results = evaluate(events, as_of)

st.subheader(patient_label(patient) if patient.get("id") else "Demo patient (synthetic)")

tab_gaps, tab_vitals, tab_chart, tab_about = st.tabs(
    ["Care gaps", "Vitals", "Problems, meds & timeline", "About"])

# ---------------- care gaps ----------------
with tab_gaps:
    counts = gap_counts(results)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gaps", counts["gap"])
    c2.metric("OK", counts["ok"])
    c3.metric("Unknown", counts["unknown"])
    c4.metric("Not applicable", counts["not_applicable"])
    for result in results:
        box = {"gap": st.error, "ok": st.success, "unknown": st.warning,
               "not_applicable": st.info}[result.status]
        box(f"**{result_title(result)}**  \n{result.detail}")
        with st.expander("Rule, evidence and explanation"):
            st.markdown(f"**Why this rule exists:** {result.rule.explanation}")
            st.markdown(f"**Window:** {result.rule.window_days} days, evaluated as of "
                        f"{as_of_date.isoformat()}")
            evidence = describe_evidence(result)
            st.markdown("**Evidence:**" if evidence else "**Evidence:** none on record")
            for line in evidence:
                st.markdown(f"- {line}")

# ---------------- vitals ----------------
with tab_vitals:
    frames = vitals_frames(events)
    left, right = st.columns(2)
    for i, (title, frame) in enumerate(frames.items()):
        with (left if i % 2 == 0 else right):
            st.markdown(f"**{title}**")
            if frame.empty:
                st.caption("No dated values on record.")
            else:
                st.line_chart(frame)

# ---------------- problems / meds / timeline ----------------
with tab_chart:
    a, b, c = st.columns(3)
    with a:
        st.markdown("**Active problems**")
        st.dataframe(simple_frame(active_problems(events)), hide_index=True,
                     use_container_width=True)
    with b:
        st.markdown("**Medications**")
        st.dataframe(simple_frame(medications(events)), hide_index=True,
                     use_container_width=True)
    with c:
        st.markdown("**Allergies**")
        st.dataframe(simple_frame(allergies(events)), hide_index=True, use_container_width=True)
    st.markdown("**Full timeline**")
    frame = events_frame(events)
    st.dataframe(frame, hide_index=True, use_container_width=True)
    st.download_button("Download timeline CSV", frame.to_csv(index=False), "timeline.csv",
                       "text/csv")

# ---------------- about ----------------
with tab_about:
    st.markdown(
        "Care-gap rules live in `rules.py` and are documented in `docs/rules.md`. Every flag "
        "shows the rule, its window, and the dated evidence. Missing or undated data is "
        "reported as **Unknown**, never silently as a gap.\n\n"
        "Data comes from a FHIR R4 server through the `fhir-timeline-cli` client, or from a "
        "bundled synthetic patient in demo mode. Never point this at real patient data.")

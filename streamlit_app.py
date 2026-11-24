"""Entry point for Streamlit Community Cloud (and `streamlit run streamlit_app.py`)."""

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
runpy.run_module("fhir_care_gaps.app", run_name="__main__")

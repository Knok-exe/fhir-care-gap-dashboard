"""Console entry point: `fhir-care-gaps` starts the Streamlit app."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    app = Path(__file__).with_name("app.py")
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app), *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())

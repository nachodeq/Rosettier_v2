"""Console launcher for the Rosettier Streamlit application."""

from __future__ import annotations

import subprocess
import sys

from rosettier_app.paths import resolve_app_path


def main() -> None:
    """Launch the Streamlit app in proper Streamlit runtime mode."""
    app_path = resolve_app_path()
    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    raise SystemExit(subprocess.call(command))

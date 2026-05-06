"""Console launcher for the Rosettier Streamlit application."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import subprocess
import sys


def resolve_app_path() -> Path:
    """Resolve the installed ``app.py`` path for ``rosettier_app``."""
    app_resource = resources.files("rosettier_app").joinpath("app.py")
    return Path(str(app_resource))


def main() -> None:
    """Launch the Streamlit app in proper Streamlit runtime mode."""
    app_path = resolve_app_path()
    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    raise SystemExit(subprocess.call(command))

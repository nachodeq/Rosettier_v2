"""Console launcher for the Rosettier Streamlit application."""

from __future__ import annotations

import subprocess
import sys
import traceback
from pathlib import Path

from rosettier_app.paths import resolve_app_path


def _log(message: str) -> None:
    print(message, flush=True)


def _build_command(app_path: Path) -> list[str]:
    return [sys.executable, "-m", "streamlit", "run", str(app_path)]


def main() -> None:
    """Launch the Streamlit app in proper Streamlit runtime mode."""
    _log("Starting Rosettier...")

    try:
        app_path = resolve_app_path()
        _log(f"Resolved app path: {app_path}")
        _log(f"Python executable: {sys.executable}")
        _log("Note: Standalone Streamlit executables can be memory-heavy on some Windows systems.")

        command = _build_command(app_path)
        _log(f"Executing command: {' '.join(command)}")
        raise SystemExit(subprocess.call(command))
    except SystemExit:
        raise
    except Exception:
        _log("Rosettier failed to launch.")
        traceback.print_exc()
        input("Press Enter to close...")
        raise SystemExit(1)

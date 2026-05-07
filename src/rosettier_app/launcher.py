"""Console launcher for the Rosettier Streamlit application."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

from streamlit.web import bootstrap

from rosettier_app.paths import resolve_app_path


def _log(message: str) -> None:
    print(message, flush=True)


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _build_bootstrap_options() -> dict[str, Any]:
    """Return Streamlit flag overrides for embedded launcher mode."""
    return {}


def _run_streamlit_app(app_path: Path) -> None:
    """Run Streamlit directly in-process to avoid recursive PyInstaller relaunches."""
    bootstrap.run(
        str(app_path),
        False,
        [],
        _build_bootstrap_options(),
    )


def main() -> None:
    """Launch the Streamlit app in proper Streamlit runtime mode."""
    _log("Starting Rosettier...")

    try:
        app_path = resolve_app_path()
        _log(f"Resolved app path: {app_path}")
        _log(f"Running in frozen mode: {_is_frozen()}")
        _log(f"Python executable: {sys.executable}")
        _log("Launching Streamlit via in-process bootstrap API (no subprocess relaunch).")

        _run_streamlit_app(app_path)
    except SystemExit:
        raise
    except Exception:
        _log("Rosettier failed to launch.")
        traceback.print_exc()
        input("Press Enter to close...")
        raise SystemExit(1)

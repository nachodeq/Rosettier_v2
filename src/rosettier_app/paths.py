"""Path resolution helpers for Rosettier app resources."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def resolve_app_path() -> Path:
    """Resolve the Streamlit ``app.py`` location in dev or installed modes."""
    app_resource = resources.files("rosettier_app").joinpath("app.py")
    return Path(str(app_resource))

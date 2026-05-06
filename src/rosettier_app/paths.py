"""Path resolution helpers for packaged Rosettier app resources."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import sys


def _bundle_root() -> Path | None:
    """Return PyInstaller extraction root when running as a frozen app."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return None


def resolve_app_path() -> Path:
    """Resolve the Streamlit ``app.py`` location in dev, installed, or bundled modes."""
    bundle_root = _bundle_root()
    if bundle_root is not None:
        return bundle_root / "rosettier_app" / "app.py"

    app_resource = resources.files("rosettier_app").joinpath("app.py")
    return Path(str(app_resource))

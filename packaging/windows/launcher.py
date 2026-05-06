"""PyInstaller entrypoint for building a standalone Rosettier Windows executable."""

from __future__ import annotations

from rosettier_app.launcher import main


if __name__ == "__main__":
    main()

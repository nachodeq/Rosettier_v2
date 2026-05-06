# Optional Windows executable build (future support)

Rosettier v2 is primarily supported through **conda + Python** on Linux, macOS, and Windows.

A Windows `.exe` build is optional future packaging for teams that need a single-file launcher.

## Important notes

- `.exe` packaging is **not required** for normal Rosettier use.
- PyInstaller (or similar) should be used only by maintainers/distributors.
- Build Windows executables on a **Windows machine** for best compatibility.
- Do **not** add PyInstaller to normal runtime/app dependencies.

## Suggested future process (maintainers)

1. Set up a clean Windows machine.
2. Create and activate the Rosettier conda environment.
3. Install Rosettier with app extras.
4. Install PyInstaller locally for packaging.
5. Build and test the executable on Windows.
6. Distribute the output together with usage notes.

## Current recommendation for users

Use the standard launch options instead:

- `rosettier-app`
- `run_rosettier_windows.bat`
- `python -m streamlit run src\\rosettier_app\\app.py`

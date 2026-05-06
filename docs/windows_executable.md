# Building a standalone Windows executable (`Rosettier.exe`)

This guide describes how maintainers can build a double-clickable `Rosettier.exe` for Windows users who do not have conda installed.

## Scope

- The executable launches Rosettier with Streamlit in the same way as:
  - `python -m streamlit run <app.py>`
- Scientific processing logic and UI behavior are unchanged.
- PyInstaller is **not** a normal runtime dependency for end users.

## Prerequisites (Windows build machine)

1. Windows 10/11
2. Python 3.10+
3. Git
4. This repository checked out locally

## Build steps

From the repository root in PowerShell:

```powershell
python -m pip install --upgrade pip
python -m pip install --no-build-isolation -e ".[app,packaging]"
pyinstaller --clean --noconfirm packaging\windows\rosettier_windows.spec
```

## Expected output

After a successful build, PyInstaller creates:

- `dist\Rosettier.exe`
- `build\` (intermediate artifacts)

You can distribute `dist\Rosettier.exe` to Windows users. On launch, it starts the Streamlit app through the packaged launcher.

## Local validation commands

Before creating the executable, validate the app and tests:

```powershell
python -m pip install --no-build-isolation -e ".[app]"
pytest -v
```

## Known limitations

- Build on Windows for Windows targets (cross-compiling from Linux/macOS is not supported here).
- First launch may be slower while PyInstaller-extracted files initialize.
- Some endpoint security tools may warn on unsigned executables.
- Streamlit still runs a local web server; users interact in their browser after launching `Rosettier.exe`.

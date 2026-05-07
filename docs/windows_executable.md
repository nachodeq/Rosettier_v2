# Building a standalone Windows executable (`Rosettier.exe`)

This guide describes how maintainers can build a double-clickable `Rosettier.exe` for Windows users who do not have conda installed.

## Scope

- The executable launches Rosettier by calling Streamlit's in-process bootstrap API (`streamlit.web.bootstrap.run`) against the bundled `app.py`.
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

## Debug-first build workflow (recommended)

Start with a debug-friendly build so startup errors are visible:

1. In `packaging/windows/rosettier_windows.spec`, keep `console=True`.
2. Build and run `dist\Rosettier.exe` from a terminal first.
3. Verify the launcher prints startup diagnostics and opens the app.
4. Only after successful validation, optionally switch to `console=False` for end-user distribution.

The launcher is expected to log:

- `Starting Rosettier...`
- resolved `app.py` path
- Python executable path
- launcher mode note (in-process Streamlit bootstrap, no subprocess relaunch)

If launch fails, the executable prints the full traceback and waits for user input before closing.


## Why the launcher must not use `sys.executable -m streamlit` under PyInstaller

In a PyInstaller-frozen app, `sys.executable` points to `Rosettier.exe` itself (not a standalone `python.exe`).
If the launcher executes `sys.executable -m streamlit run ...`, the EXE relaunches itself recursively.
That recursion duplicates runtime state and can trigger severe memory pressure, pagefile exhaustion, and secondary import failures (for example NumPy DLL import errors).

Current launcher architecture:

- resolve `app.py` with `resolve_app_path()` for both normal and frozen (`sys._MEIPASS`) modes.
- print startup diagnostics (startup banner, resolved path, frozen mode, executable path).
- call `streamlit.web.bootstrap.run(...)` directly in the same process.
- on error, print traceback and wait for Enter so logs remain visible when `console=True`.

This design prevents recursive self-launch and avoids spawning a second Python runtime.

## Resource guidance and memory limitations

- Recommended build machine memory: **16 GB RAM minimum** (32 GB preferred for smoother builds).
- Recommended target machine memory for `Rosettier.exe`: **8 GB RAM minimum**.
- Always validate a **debug build first** (`console=True`) before any silent/windowed packaging changes.
- If the standalone executable closes due to memory limits on user machines, distribute Rosettier via the normal conda workflow instead of the standalone EXE.
- Known limitation: standalone Streamlit executables can be relatively heavy compared with conda-based runs.

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

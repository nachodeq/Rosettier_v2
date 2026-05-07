# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).resolve().parents[1]

app_datas = [(str(project_root / "src" / "rosettier_app" / "app.py"), "rosettier_app")]

# Keep hidden imports focused to reduce bundle size and startup memory pressure.
hiddenimports = ["streamlit.web.cli"]

# Exclude development and heavy optional modules not required by Rosettier runtime.
excludes = [
    "tests",
    "pytest",
    "scipy",
    "notebook",
    "jupyter",
    "jupyterlab",
    "IPython",
    "ipykernel",
    "tkinter",
    "matplotlib.backends.backend_qt5agg",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_wx",
    "matplotlib.backends.backend_wxagg",
]


a = Analysis(
    [str(project_root / "packaging" / "windows" / "launcher.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=app_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Rosettier",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

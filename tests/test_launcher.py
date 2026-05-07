from pathlib import Path

import pytest

from rosettier_app import launcher
from rosettier_app import paths


def test_launcher_imports_and_exposes_main():
    assert launcher is not None
    assert callable(launcher.main)


def test_build_command_uses_python_module_streamlit(monkeypatch):
    monkeypatch.setattr(launcher.sys, "executable", "C:/Python/python.exe")

    command = launcher._build_command(Path("C:/Rosettier/app.py"))

    assert command == [
        "C:/Python/python.exe",
        "-m",
        "streamlit",
        "run",
        "C:/Rosettier/app.py",
    ]


def test_resolve_app_path_points_to_packaged_app():
    app_path = paths.resolve_app_path()
    assert isinstance(app_path, Path)
    assert app_path.name == "app.py"
    assert app_path.exists()


def test_resolve_app_path_uses_meipass_when_frozen(monkeypatch, tmp_path):
    frozen_app = tmp_path / "rosettier_app" / "app.py"
    frozen_app.parent.mkdir(parents=True)
    frozen_app.write_text("# bundled app")

    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert paths.resolve_app_path() == frozen_app


def test_launcher_prints_debug_info_and_invokes_subprocess(monkeypatch, capsys):
    monkeypatch.setattr(launcher, "resolve_app_path", lambda: Path("C:/bundle/rosettier_app/app.py"))
    monkeypatch.setattr(launcher.sys, "executable", "C:/Python/python.exe")

    called = {}

    def fake_call(command):
        called["command"] = command
        return 0

    monkeypatch.setattr(launcher.subprocess, "call", fake_call)

    with pytest.raises(SystemExit) as exc:
        launcher.main()

    assert exc.value.code == 0
    assert called["command"] == [
        "C:/Python/python.exe",
        "-m",
        "streamlit",
        "run",
        "C:/bundle/rosettier_app/app.py",
    ]

    output = capsys.readouterr().out
    assert "Starting Rosettier..." in output
    assert "Resolved app path: C:/bundle/rosettier_app/app.py" in output
    assert "Python executable: C:/Python/python.exe" in output
    assert "Standalone Streamlit executables can be memory-heavy" in output
    assert "Executing command: C:/Python/python.exe -m streamlit run C:/bundle/rosettier_app/app.py" in output


def test_launcher_prints_traceback_and_waits_for_input_on_error(monkeypatch, capsys):
    monkeypatch.setattr(launcher, "resolve_app_path", lambda: Path("C:/bundle/rosettier_app/app.py"))
    monkeypatch.setattr(launcher.sys, "executable", "C:/Python/python.exe")

    monkeypatch.setattr(launcher.subprocess, "call", lambda _command: (_ for _ in ()).throw(RuntimeError("boom")))

    prompted = {}

    def fake_input(prompt):
        prompted["prompt"] = prompt
        return ""

    monkeypatch.setattr("builtins.input", fake_input)

    with pytest.raises(SystemExit) as exc:
        launcher.main()

    assert exc.value.code == 1
    assert prompted["prompt"] == "Press Enter to close..."

    out_err = capsys.readouterr()
    assert "Rosettier failed to launch." in out_err.out
    assert "RuntimeError: boom" in out_err.err

from pathlib import Path

import pytest

from rosettier_app import launcher
from rosettier_app import paths


def test_launcher_imports_and_exposes_main():
    assert launcher is not None
    assert callable(launcher.main)


def test_build_bootstrap_options_defaults_empty():
    assert launcher._build_bootstrap_options() == {}


def test_run_streamlit_app_uses_bootstrap(monkeypatch):
    called = {}

    def fake_run(main_script_path, is_hello, args, flag_options):
        called["main_script_path"] = main_script_path
        called["is_hello"] = is_hello
        called["args"] = args
        called["flag_options"] = flag_options

    monkeypatch.setattr(launcher.bootstrap, "run", fake_run)
    monkeypatch.setattr(launcher, "_build_bootstrap_options", lambda: {"server.headless": True})

    launcher._run_streamlit_app(Path("/tmp/rosettier_app/app.py"))

    assert called == {
        "main_script_path": "/tmp/rosettier_app/app.py",
        "is_hello": False,
        "args": [],
        "flag_options": {"server.headless": True},
    }


def test_resolve_app_path_points_to_packaged_app():
    app_path = paths.resolve_app_path()
    assert isinstance(app_path, Path)
    assert app_path.name == "app.py"
    assert app_path.exists()


def test_launcher_prints_debug_info_and_invokes_bootstrap(monkeypatch, capsys):
    monkeypatch.setattr(launcher, "resolve_app_path", lambda: Path("/tmp/rosettier_app/app.py"))

    called = {}

    def fake_run_streamlit_app(app_path):
        called["app_path"] = app_path

    monkeypatch.setattr(launcher, "_run_streamlit_app", fake_run_streamlit_app)

    launcher.main()

    assert called["app_path"] == Path("/tmp/rosettier_app/app.py")

    output = capsys.readouterr().out
    assert "Starting Rosettier..." in output
    assert "Resolved app path: /tmp/rosettier_app/app.py" in output
    assert "Launching Streamlit via in-process bootstrap API." in output


def test_launcher_prints_traceback_and_waits_for_input_on_error(monkeypatch, capsys):
    monkeypatch.setattr(launcher, "resolve_app_path", lambda: Path("/tmp/rosettier_app/app.py"))

    monkeypatch.setattr(
        launcher,
        "_run_streamlit_app",
        lambda _app_path: (_ for _ in ()).throw(RuntimeError("boom")),
    )

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

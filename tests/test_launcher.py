from pathlib import Path

from rosettier_app import launcher
from rosettier_app import paths


def test_launcher_imports_and_exposes_main():
    assert launcher is not None
    assert callable(launcher.main)


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

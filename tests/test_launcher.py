from pathlib import Path

from rosettier_app import launcher


def test_launcher_imports_and_exposes_main():
    assert launcher is not None
    assert callable(launcher.main)


def test_resolve_app_path_points_to_packaged_app():
    app_path = launcher.resolve_app_path()
    assert isinstance(app_path, Path)
    assert app_path.name == "app.py"
    assert app_path.exists()

from rosettier_app import app


def test_app_module_imports():
    assert app is not None


def test_main_exists():
    assert callable(app.main)

# Installation

## Requirements

- Python 3.10+
- Local environment manager (venv or conda)

## Pip editable install (recommended)

```bash
python -m pip install --upgrade pip
python -m pip install --no-build-isolation -e ".[app]"
```

## Optional developer install

```bash
python -m pip install -e ".[dev,app,analysis]"
```

## Verify install

```bash
python -c "import rosettier; print('rosettier import: OK')"
python -c "import rosettier_app; print('rosettier_app import: OK')"
```

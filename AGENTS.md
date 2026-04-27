# Rosettier v2 agent instructions

## Setup

Install all dependencies with:

```bash
python -m pip install -e ".[dev,app,analysis]"
```

Run tests with:

```bash
pytest -v
```

## Dependency policy

If a new dependency is required:

1. Add it to `pyproject.toml`.
2. Use `[project.dependencies]` only for packages needed by users.
3. Use `[project.optional-dependencies].dev` for testing/linting tools.
4. Use app-specific extras for UI packages.
5. Prefer stable open-source packages available on PyPI and conda-forge.
6. Do not remove or weaken tests because dependencies are missing.

After changing dependencies, run:

```bash
python -m pip install -e ".[dev,app,analysis]"
pytest -v
```

## Project rules

Keep the core package independent of Streamlit or any UI framework.

Put reusable logic in:

```text
src/rosettier/
```

Put tests in:

```text
tests/
```

Prefer small, focused commits.

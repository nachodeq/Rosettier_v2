# Release process

This document describes the recommended release workflow for Rosettier v2.

## 1) Update version metadata

Update version consistently in:

- `pyproject.toml`
- `CITATION.cff`
- `CHANGELOG.md`
- any user-facing version mentions in docs

## 2) Refresh environment and install

```bash
python -m pip install -e ".[dev,app,analysis]"
python -m pip install --no-build-isolation -e ".[app]"
```

## 3) Run tests

```bash
pytest -v
```

## 4) Validate launch path

```bash
rosettier-app
```

Perform a short manual smoke test with files from `examples/`.

## 5) Commit release prep

- Ensure docs are updated (README, installation, examples, screenshots checklist).
- Ensure changelog entry is complete.
- Commit with a release-prep message.

## 6) Tag release

```bash
git tag -a vX.Y.Z -m "Rosettier vX.Y.Z"
git push origin vX.Y.Z
```

## 7) Create GitHub release

On GitHub:

1. Draft release from tag `vX.Y.Z`.
2. Paste highlights from changelog.
3. Attach source archives if needed.
4. Publish release.


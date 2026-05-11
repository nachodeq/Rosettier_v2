# Quickstart

## 1) Install

```bash
python -m pip install --no-build-isolation -e ".[app]"
```

## 2) Launch app

```bash
rosettier-app
```

## 3) Typical workflow

1. Create or load a Rosetta (metadata) table.
2. Upload plate-reader time-series data.
3. Merge metadata + measurements.
4. Review QC summaries.
5. Extract features (endpoint, AUC, max slope, max value, time-to-threshold).
6. Export resulting tables.

## 4) Example data

Use fixtures in `examples/fixtures/` to test the flow locally.

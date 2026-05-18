# Rosettier v2

Rosettier v2 is an open source tool for **plate-reader growth curve workflows**. It combines:

- a reusable Python analysis package (`rosettier`), and
- a local Streamlit application launcher (`rosettier-app`)

for creating Rosetta (metadata) plate maps, importing measurements, running exploratory analysis, and exporting analysis-ready outputs.

## Key features

- Rosetta (metadata) support for **96-well and 384-well** plates.
- Plate-reader time-series parsing and tidy conversion.
- Merge of measurement time-series with Rosetta (metadata).
- Core QC summaries and feature extraction (endpoint, AUC, max slope, max value, time-to-threshold).

## Screenshots

Screenshots are documented in `docs/screenshots/README.md` and should be captured from the current release UI:

- App home / data-loading view
- Rosetta (metadata) creation view (96-well)
- Rosetta (metadata) creation view (384-well)
- Analysis/QC summary view
- Export/results view

See `docs/screenshots/` for placeholder markdown files and naming conventions.

## Installation

### Recommended: conda/Miniforge environment

```bash
conda env create -f environment.yml
conda activate rosettier-v2
```

Then launch:

```bash
rosettier-app
```

### Alternative: pip editable install (local development/testing)

```bash
python -m pip install --no-build-isolation -e ".[app]"
rosettier-app
```

Detailed platform instructions: `docs/installation.md`.

## Quickstart

1. Launch `rosettier-app`.
2. Create or import a Rosetta (metadata) table.
3. Import plate-reader measurement data.
4. Run merge, QC, and feature extraction.
5. Export tables for downstream statistical analysis.

See `docs/quickstart.md` for a concise walkthrough.

## Workflow overview

### 1) Create Rosetta (metadata)

Build a plate map for 96- or 384-well experiments with metadata columns such as condition, strain, dose, and replicate.

### 2) Import measurements

Load plate-reader time-series exports and parse to tidy records.

### 3) Analyze data

Merge measurements with Rosetta (metadata), review QC summaries, and compute derived features.

### 4) Export results

Export tidy time-series tables, merged tables, and feature summaries for downstream analysis.

## Example input formats

- Rosetta (metadata) tables: `.csv`, `.tsv`
- Plate-reader measurements: `.tsv`, `.txt` (tabular exports with well columns)
- Export outputs: `.csv`, `.tsv`

More schema guidance: `docs/input_formats.md`.

## Example datasets

The `examples/` folder includes reproducible sample datasets:

- `96_Rosetta.tsv`
- `96_OD_Measurements.tsv`
- `384_Rosetta.tsv`
- `384_OD_Measurements.tsv`

Dataset descriptions: `examples/README.md`.

## Citation

if Rosettier was used in your paper, please cite: XXXXX


## License

MIT License. See `LICENSE`.

## Troubleshooting

See `docs/installation.md` for common issues, including:

- `conda` command not found
- `rosettier-app` not found
- Streamlit port already in use
- editable install issues



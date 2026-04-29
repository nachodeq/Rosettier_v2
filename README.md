# Rosettier v2

Rosettier v2 is a tool for plate-based assay workflows. It combines a reusable Python core (`rosettier`) with a Streamlit app (`rosettier_app`) to help scientists:

- build or import Rosetta plate maps,
- parse plate-reader time-series files,
- merge measurements with plate metadata,
- run QC and feature extraction,
- export analysis-ready tables and visual outputs.

## Quick start

### 1) Install (local, pip)

#### Python package + app

```bash
python -m pip install --no-build-isolation -e ".[app]"
```

#### Full developer install

```bash
python -m pip install -e ".[dev,app]"
```

### 2) Conda environment install

```bash
conda create -n rosettier python=3.11
conda activate rosettier
python -m pip install --no-build-isolation -e ".[app]"
```

### 3) Launch the app

Preferred entrypoint:

```bash
rosettier-app
```

Alternative:

```bash
python -m streamlit run src/rosettier_app/app.py
```

## Supported workflows

1. **Create Rosetta layouts** (96/384-well) for conditions, treatments, and metadata.
2. **Load input data** from plate-reader exports and Rosetta tables.
3. **Analyze data** with QC and feature extraction (e.g., endpoint, AUC, max slope, time-to-threshold).
4. **Export results** as tabular outputs for downstream statistics and reporting.

See `docs/` for step-by-step guides for every stage: installation, Rosetta creation, data loading, analysis, and exports (`docs/installation.md`, `docs/quickstart.md`, `docs/create_rosetta.md`, `docs/analyze_data.md`, `docs/input_formats.md`).

## Input file formats

- **Rosetta layout files**: `.csv` or `.tsv` with well-level metadata.
- **Plate-reader data**: delimited text tables compatible with Rosettier parser assumptions.
- **Output tables**: `.csv`/`.tsv` exports suitable for analysis pipelines.

Detailed schema notes: `docs/input_formats.md`.

## Examples

### Python API example (parse 384-well fixture)

```bash
python -c "import pandas as pd; from rosettier.io import parse_plate_reader_wide; df = pd.read_csv('examples/fixtures/plate_reader_384_example.txt', sep='\t'); tidy = parse_plate_reader_wide(df, plate_size=384); print(tidy.head())"
```

### End-to-end examples

Use the guides in `docs/` for complete workflows:

- `docs/quickstart.md`
- `docs/create_rosetta.md`
- `docs/analyze_data.md`
- `docs/input_formats.md`

## Citation

If you use Rosettier v2 in a publication, please cite the software release.

Cite using the metadata in `CITATION.cff`. A DOI will be added once a Zenodo archive is created.

## License

This project is distributed under the MIT License. See `LICENSE`.

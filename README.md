# Rosettier v2

Rosettier v2 is a tool for plate-based assay workflows. It combines a reusable Python core (`rosettier`) with a Streamlit app (`rosettier_app`) to help scientists:

- build or import Rosetta plate maps,
- parse plate-reader time-series files,
- merge measurements with plate metadata,
- run QC and feature extraction,
- export analysis-ready tables and visual outputs.

## Quick start

### 1) Conda install (primary supported route)

Use the provided environment file on Linux, macOS, or Windows:

```bash
conda env create -f environment.yml
conda activate rosettier-v2
```

This installs core runtime/app dependencies and performs editable install with app extras (`-e .[app]`).

### 2) Alternative pip install

```bash
python -m pip install --no-build-isolation -e ".[app]"
```

Developer install:

```bash
python -m pip install -e ".[dev,app]"
```

### 3) Launch the app

Preferred entrypoint:

```bash
rosettier-app
```

Fallback launch scripts:

- Linux/macOS:

  ```bash
  ./run_rosettier.sh
  ```

- Windows:

  ```bat
  run_rosettier_windows.bat
  ```

Direct Streamlit fallback:

- Linux/macOS:

  ```bash
  python -m streamlit run src/rosettier_app/app.py
  ```

- Windows:

  ```bat
  python -m streamlit run src\rosettier_app\app.py
  ```

## Zip/USB distribution workflow

For internal offline-style handoff (for teams that still use conda):

1. Bundle repository files (zip or USB copy), including `environment.yml` and launch scripts.
2. On target machine, extract files and open a terminal in the project directory.
3. Create environment: `conda env create -f environment.yml`.
4. Activate environment: `conda activate rosettier-v2`.
5. Launch via `rosettier-app` (or fallback script).

## Supported workflows

1. **Create Rosetta layouts** (96/384-well) for conditions, treatments, and metadata.
2. **Load input data** from plate-reader exports and Rosetta tables.
3. **Analyze data** with QC and feature extraction (e.g., endpoint, AUC, max slope, time-to-threshold).
4. **Export results** as tabular outputs for downstream statistics and reporting.

See `docs/` for step-by-step guides: installation, Rosetta creation, data loading, analysis, and exports (`docs/installation.md`, `docs/quickstart.md`, `docs/create_rosetta.md`, `docs/analyze_data.md`, `docs/input_formats.md`).

## Input file formats

- **Rosetta layout files**: `.csv` or `.tsv` with well-level metadata.
- **Plate-reader data**: delimited text tables compatible with Rosettier parser assumptions.
- **Output tables**: `.csv`/`.tsv` exports suitable for analysis pipelines.

Detailed schema notes: `docs/input_formats.md`.

## Citation

If you use Rosettier v2 in a publication, please cite the software release.

Cite using the metadata in `CITATION.cff`. A DOI will be added once a Zenodo archive is created.

## License

This project is distributed under the MIT License. See `LICENSE`.

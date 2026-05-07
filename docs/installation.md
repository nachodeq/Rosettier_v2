# Installation

## Requirements

- Conda (Miniconda/Anaconda/Mambaforge)
- Python 3.10+

## Primary setup (Linux/macOS/Windows via conda)

From the project root:

```bash
conda env create -f environment.yml
conda activate rosettier-v2
```

This environment includes:

- python
- pandas
- streamlit
- plotly
- matplotlib
- pytest
- pip
- editable install of Rosettier app extras (`-e .[app]`)

## Launch options

Preferred console entrypoint:

```bash
rosettier-app
```

Fallback scripts:

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

## Optional developer install

```bash
python -m pip install -e ".[dev,app,analysis]"
```

## Verification

```bash
python -c "import rosettier; print('rosettier import: OK')"
python -c "import rosettier_app; print('rosettier_app import: OK')"
```

## Zip/USB distribution

For internal sharing without publishing a package index:

1. Copy this repository to zip or USB.
2. On the destination machine, extract/open in terminal.
3. Run `conda env create -f environment.yml`.
4. Run `conda activate rosettier-v2`.
5. Launch with `rosettier-app` (or platform fallback script).


# Installation

This guide documents the supported local installation methods for Rosettier v2.

## Supported setup model

Rosettier v2 is distributed as source and run in a local Python environment. The recommended cross-platform approach is conda/Miniforge.

## Linux (conda)

```bash
conda env create -f environment.yml
conda activate rosettier-v2
rosettier-app
```

## macOS (conda)

```bash
conda env create -f environment.yml
conda activate rosettier-v2
rosettier-app
```

## Windows (Miniforge/conda)

Open **Miniforge Prompt** (or Anaconda Prompt), then run:

```bat
conda env create -f environment.yml
conda activate rosettier-v2
rosettier-app
```

If needed, fallback launcher:

```bat
run_rosettier_windows.bat
```

## Alternative editable install (no conda env file)

From the repository root:

```bash
python -m pip install --no-build-isolation -e ".[app,dev,analysis]"
pytest -v
rosettier-app
```

## Verify installation

```bash
python -c "import rosettier; print('rosettier import: OK')"
python -c "import rosettier_app; print('rosettier_app import: OK')"
```

## Troubleshooting

### 1) `conda: command not found`

- Install Miniforge (recommended) or Miniconda.
- Close and reopen your terminal.
- Confirm with `conda --version`.

### 2) `rosettier-app: command not found`

- Ensure the correct environment is active: `conda activate rosettier-v2`.
- Reinstall app entry points:

  ```bash
  python -m pip install --no-build-isolation -e ".[app,dev,analysis]"
  ```

- Verify script path with:

  ```bash
  python -c "import shutil; print(shutil.which('rosettier-app'))"
  ```

### 3) Streamlit port already in use

Launch on another port:

```bash
python -m streamlit run src/rosettier_app/app.py --server.port 8502
```

### 4) Editable install fails

- Upgrade packaging tools:

  ```bash
  python -m pip install --upgrade pip setuptools wheel
  ```

- Retry install:

  ```bash
  python -m pip install --no-build-isolation -e ".[app,dev,analysis]"
  ```

- Confirm you are running from the repository root containing `pyproject.toml`.


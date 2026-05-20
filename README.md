# Rosettier v2

Rosettier v2 is an open-source toolkit for plate-reader growth curve workflows that combines a reusable Python analysis package with a local Streamlit app to create Rosetta metadata maps, import measurements, analyze growth data, and export analysis-ready outputs.

## Key features

- Rosetta (metadata) support for 96-well and 384-well plates.
- Plate-reader time-series parsing and tidy conversion.
- Merge of measurements with Rosetta metadata.
- QC summaries and feature extraction (endpoint, AUC, max slope, max value, time-to-threshold).

## Installation from downloaded package (quick)

```bash
python -m pip install --no-build-isolation -e ".[app,dev]"
pytest -v
rosettier-app
```

For detailed installation instructions and troubleshooting, see `docs/installation.md`.

## Conda install:

Choose one installation path for Miniconda, then continue with Rosettier environment setup.

### Option A — command line download/install (Linux/macOS)

1. Download the installer script:
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-$(uname)-$(uname -m).sh -O miniconda.sh
   ```
2. Run the installer:
   ```bash
   bash miniconda.sh
   ```
3. Restart your shell, then verify:
   ```bash
   conda --version
   ```

### Option B — click-to-download installer

1. Open the Miniconda installer page in your browser:  
   https://www.anaconda.com/docs/getting-started/miniconda/install
2. Download the installer for your operating system and CPU architecture.
3. Run the downloaded installer (`.sh` on Linux/macOS, `.exe` on Windows).
4. Open a new terminal and verify:
   ```bash
   conda --version
   ```

### Create and activate a Rosettier Conda environment

```bash
conda create -n rosettier-v2 python=3.11 -y
conda activate rosettier-v2
python -m pip install --no-build-isolation -e ".[app,dev]"
pytest -v
```

## Docker quick start

```bash
docker build -t rosettier-v2 .
docker run --rm -p 8501:8501 rosettier-v2
```

For full Docker requirements and troubleshooting, see `docs/docker.md`.

## Docker install:

Use one of the options below, then run the Rosettier Docker commands.

### Option A — command line install (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker --version
```

Optional (run Docker without `sudo`):
```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker run hello-world
```

### Option B — click-to-download installer

1. Open Docker Desktop download page:  
   https://www.docker.com/products/docker-desktop/
2. Download Docker Desktop for your OS (Windows/macOS/Linux desktop).
3. Install Docker Desktop and launch it.
4. Verify from terminal:
   ```bash
   docker --version
   docker compose version
   ```

## Basic workflow

Create Rosetta → Import measurements → Analyze data → Export results

## Documentation

- Installation and troubleshooting: `docs/installation.md`
- Docker guide: `docs/docker.md`
- Input formats: `docs/input_formats.md`
- Screenshots: `docs/screenshots/README.md`
- Example datasets: `examples/README.md`
- Publication notes: `docs/publication_notes.md`
- Video tutorial example `docs/Tutorial_analysis_rosettier.mp4`

Screenshots and naming conventions are described in `docs/screenshots/README.md`.

Examples are available in `examples/`.

## Citation

If you use Rosettier in your work, please cite the software using the metadata in `CITATION.cff`. A DOI will be added after archival release.

## License

MIT License. See `LICENSE`.

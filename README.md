# Rosettier v2

Rosettier v2 is an open-source toolkit for plate-reader growth curve workflows that combines a reusable Python analysis package with a local Streamlit app to create Rosetta metadata maps, import measurements, analyze growth data, and export analysis-ready outputs.

## Key features

- Rosetta (metadata) support for 96-well and 384-well plates.
- Plate-reader time-series parsing and tidy conversion.
- Merge of measurements with Rosetta metadata.
- QC summaries and feature extraction (endpoint, AUC, max slope, max value, time-to-threshold).

## Installation (quick)

```bash
python -m pip install --no-build-isolation -e ".[app,dev]"
pytest -v
rosettier-app
```

For detailed installation instructions and troubleshooting, see `docs/installation.md`.

## Docker (quick)

```bash
docker build -t rosettier-v2 .
docker run --rm -p 8501:8501 rosettier-v2
```

For full Docker requirements and troubleshooting, see `docs/docker.md`.

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

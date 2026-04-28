# Rosettier v2

## Local app install

```bash
python -m pip install -e ".[app]"
```

## Offline Plotly exports (HTML)

The Streamlit app exports plots using the same Plotly figure object shown in the preview.

- **HTML** exports are fully offline/self-contained and do not require Chrome or Kaleido.
- **PNG/SVG** exports require Kaleido plus a local Chrome installation.

Local setup for full app + static export:

```bash
python -m pip install -e ".[app]"
plotly_get_chrome
```

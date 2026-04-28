# Rosettier v2

## Local app install

```bash
python -m pip install -e ".[app]"
```

## Plot exports (PNG/SVG)

The Streamlit app exports plots using the same Plotly figure object shown in the preview.

- **PNG/SVG** exports use a local matplotlib backend (no Chrome dependency).

Local setup for full app + static export:

```bash
python -m pip install -e ".[app]"
```

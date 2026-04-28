# Rosettier v2

## Local app install

```bash
python -m pip install -e ".[app]"
```

## Offline Plotly exports (HTML / PNG / SVG)

The Streamlit app exports plots using the same Plotly figure object shown in the preview.

- **HTML** exports are fully offline/self-contained.
- **PNG/SVG** exports use **Kaleido** and require a local Chrome/Chromium installation discoverable on your machine.
- The app **does not** run `plotly_get_chrome` automatically.

If PNG/SVG export is unavailable, install Chrome once locally and restart the app. For manual Plotly setup, you can also run:

```bash
plotly_get_chrome
```

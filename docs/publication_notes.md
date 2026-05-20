# Publication notes

Use citation metadata from `CITATION.cff` when referencing Rosettier in manuscripts, reports, or software records.

A DOI will be added after archival release.

## BMC Bioinformatics readiness checklist

- Capture and archive representative UI screenshots (main workflow + exports).
- Run reproducibility verification on shipped examples:
  - `python scripts/verify_examples.py`
- Ensure CI is passing on GitHub Actions before submission.
- Create and push a release tag (e.g., `vX.Y.Z`) tied to manuscript version.
- Mint Zenodo DOI from tagged GitHub release and add DOI to `CITATION.cff`.
- Include a short benchmark/performance note in manuscript supplementary materials.

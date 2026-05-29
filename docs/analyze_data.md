# Analyze Data

## Inputs

Rosettier has two app analysis modes that share the same Rosetta (metadata) layout model.

### Growth curves / time series

Use this mode when each well has repeated measurements across time or cycles. Inputs are:

- Plate-reader time-series measurements with one time/cycle column and one column per well.
- Rosetta (metadata) table for the matching plate.

### Point measurements

Use this mode when each well has one endpoint or snapshot value per signal. Inputs are:

- One or more point-measurement files, such as OD, GFP, luminescence, or other endpoint readouts.
- Either a long table keyed by `Well` (for example `Well;OD;plate`) or a plate-shaped matrix with row labels (`A`-`H` or `A`-`P`) and numeric column headers.
- Rosetta (metadata) from the current app session or an uploaded CSV/TSV/TXT layout.

## Growth-curve analysis flow

1. Parse raw measurements into tidy form.
2. Merge measurements with Rosetta (metadata) by `well`.
3. Run QC summary checks.
4. Extract derived features:
   - endpoint
   - area under curve (AUC)
   - maximum slope
   - maximum value
   - time to threshold
5. Export analysis-ready results.

## Point-measurement analysis flow

1. Choose the Rosetta (metadata) source.
2. Upload one or more single-timepoint measurement files.
3. Name each signal and, for long-format files, choose or auto-detect the value column.
4. Parse each file into tidy per-well records.
5. Merge measurements with Rosetta (metadata) by `well`.
6. Review per-signal plate heatmaps and merged tables.
7. Export combined point-measurement results for downstream analysis.

## Output artifacts

After analysis, Rosettier exports analysis-ready files you can use directly in downstream statistics/reporting:

- **Tidy time-series table**: one row per `(well, time)` with parsed measurement values and plate coordinates.
- **Merged long table**: tidy measurements joined with Rosetta (metadata) columns (condition, treatment, dose, etc.).
- **Feature summary table**: per-well derived metrics such as endpoint, AUC, maximum slope, maximum value, and time-to-threshold.
- **QC summary outputs**: checks and summary views to help detect parsing/metadata issues before interpretation.
- **Point-measurement exports**: per-signal tidy tables, metadata-merged point measurements, plate heatmap figures, and combined multi-signal result tables.

Use these outputs as inputs to statistical modeling, visualization notebooks, or LIMS/reporting pipelines.

## Reproducibility tips

- Keep a versioned Rosetta (metadata) table for each run.
- Save raw input files alongside outputs.
- Record software version (`0.2.0`) with exported results.

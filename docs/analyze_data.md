# Analyze Data

## Inputs

- Plate-reader measurements.
- Rosetta layout table for the matching plate.

## Analysis flow

1. Parse raw measurements into tidy form.
2. Merge measurements with Rosetta metadata by `well`.
3. Run QC summary checks.
4. Extract derived features:
   - endpoint
   - area under curve (AUC)
   - maximum slope
   - maximum value
   - time to threshold
5. Export analysis-ready results.

## Output artifacts

After analysis, Rosettier exports analysis-ready files you can use directly in downstream statistics/reporting:

- **Tidy time-series table**: one row per `(well, time)` with parsed measurement values and plate coordinates.
- **Merged long table**: tidy measurements joined with Rosetta metadata columns (condition, treatment, dose, etc.).
- **Feature summary table**: per-well derived metrics such as endpoint, AUC, maximum slope, maximum value, and time-to-threshold.
- **QC summary outputs**: checks and summary views to help detect parsing/layout issues before interpretation.

Use these outputs as inputs to statistical modeling, visualization notebooks, or LIMS/reporting pipelines.

## Reproducibility tips

- Keep a versioned Rosetta layout for each run.
- Save raw input files alongside outputs.
- Record software version (`0.2.0`) with exported results.

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

## Reproducibility tips

- Keep a versioned Rosetta layout for each run.
- Save raw input files alongside outputs.
- Record software version (`0.2.0`) with exported results.

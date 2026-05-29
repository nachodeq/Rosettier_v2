# Example datasets

Rosettier v2 ships with paired Rosetta (metadata), time-series, and point-measurement examples for reproducible local testing.

## 96-well example

- `96_Rosetta.tsv`: Rosetta (metadata) for a 96-well plate.
- `96_OD_Measurements.tsv`: matching optical-density time-series measurements.
- `96_Point_OD.tsv`: long-format single-timepoint OD point measurements for the same 96-well layout.
- `96_Point_GFP_matrix.tsv`: plate-matrix single-timepoint GFP point measurements for the same 96-well layout.

## 384-well example

- `384_Rosetta.tsv`: Rosetta (metadata) for a 384-well plate.
- `384_OD_Measurements.tsv`: matching optical-density time-series measurements.

## Suggested usage

1. Start `rosettier-app`.
2. Load a Rosetta (metadata) example and the matching measurement file.
3. For growth curves, run the merge/QC/features flow.
4. For point measurements, open **Analyze Point Measurements**, load `96_Point_OD.tsv` and/or `96_Point_GFP_matrix.tsv`, then run point-measurement analysis.
5. Export result tables to verify local execution.

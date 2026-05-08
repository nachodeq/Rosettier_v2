# Example datasets

Rosettier v2 ships with paired Rosetta layout and measurement examples for reproducible local testing.

## 96-well example

- `96_Rosetta.tsv`: Rosetta layout metadata for a 96-well plate.
- `96_OD_Measurements.tsv`: matching optical-density time-series measurements.

## 384-well example

- `384_Rosetta.tsv`: Rosetta layout metadata for a 384-well plate.
- `384_OD_Measurements.tsv`: matching optical-density time-series measurements.

## Suggested usage

1. Start `rosettier-app`.
2. Load a Rosetta example and the matching measurement file.
3. Run merge/QC/features flow.
4. Export result tables to verify local execution.

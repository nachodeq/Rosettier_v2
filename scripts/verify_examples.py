"""Run basic reproducibility checks on shipped Rosettier example datasets."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rosettier.features import extract_features
from rosettier.io import parse_plate_reader_wide
from rosettier.layout import merge_measurements_with_layout
from rosettier.plates import PlateSpec

REQUIRED_FEATURE_COLUMNS = {"well", "row", "column", "endpoint", "auc", "max_slope", "max_value"}

EXAMPLES = [
    {"name": "96-well", "plate_size": 96, "measurement": "96_OD_Measurements.tsv", "layout": "96_Rosetta.tsv"},
    {"name": "384-well", "plate_size": 384, "measurement": "384_OD_Measurements.tsv", "layout": "384_Rosetta.tsv"},
]


def _verify_case(base: Path, case: dict[str, object]) -> None:
    plate_size = int(case["plate_size"])
    expected_wells = len(PlateSpec.from_size(plate_size).canonical_wells())

    measurement_df = pd.read_csv(base / str(case["measurement"]), sep="\t")
    layout_df = pd.read_csv(base / str(case["layout"]), sep="\t").rename(columns={"Well": "well"})

    tidy = parse_plate_reader_wide(measurement_df, plate_size=plate_size, time_col="Time")
    tidy_with_layout = merge_measurements_with_layout(tidy, layout_df, plate_size=plate_size)
    features = extract_features(tidy_with_layout)

    non_empty_rows = tidy_with_layout.dropna(subset=["value"])
    if non_empty_rows.empty:
        raise AssertionError(f"{case['name']}: parsed tidy table has no non-empty values")

    wells_in_tidy = tidy_with_layout["well"].nunique()
    if wells_in_tidy != expected_wells:
        raise AssertionError(f"{case['name']}: expected {expected_wells} wells, got {wells_in_tidy}")

    if len(features) != expected_wells:
        raise AssertionError(f"{case['name']}: expected {expected_wells} feature rows, got {len(features)}")

    missing_cols = REQUIRED_FEATURE_COLUMNS.difference(features.columns)
    if missing_cols:
        raise AssertionError(f"{case['name']}: missing feature columns: {sorted(missing_cols)}")

    print(f"[OK] {case['name']}: wells={expected_wells}, tidy_rows={len(tidy_with_layout)}, feature_rows={len(features)}")


def main() -> None:
    examples_dir = Path(__file__).resolve().parents[1] / "examples"
    for case in EXAMPLES:
        _verify_case(examples_dir, case)
    print("All example reproducibility checks passed.")


if __name__ == "__main__":
    main()

import pandas as pd

from rosettier.export import prepare_plate_matrix, summarize_by_group
from rosettier.features import extract_features
from rosettier.io import parse_timeseries_wide, wide_to_long
from rosettier.layout import merge_measurements_with_layout
from rosettier.plates import PlateSpec
from rosettier.qc import qc_summary


def test_full_pipeline_canonical_schema_flow():
    wells = PlateSpec.from_size(96).canonical_wells()

    wide_df = pd.DataFrame(
        {
            "time": [0.0, 1.0, 2.0],
            **{well: [float(i), float(i + 1), float(i + 2)] for i, well in enumerate(wells)},
        }
    )

    parsed = parse_timeseries_wide(wide_df, plate_size=96)
    tidy = wide_to_long(parsed, plate_size=96)

    layout_df = pd.DataFrame(
        {
            "well": wells,
            "group": ["treated" if idx % 2 == 0 else "control" for idx in range(len(wells))],
        }
    )
    merged = merge_measurements_with_layout(tidy, layout_df, plate_size=96)

    qc = qc_summary(merged)
    assert {"missing", "constant_wells", "outlier_wells", "edge_effects"}.issubset(qc.keys())

    feature_table = extract_features(merged, threshold=1.0)
    assert {"well", "row", "column", "endpoint", "auc", "max_slope", "time_to_threshold", "group"}.issubset(
        feature_table.columns
    )

    endpoint_tidy = feature_table[["well", "row", "column", "endpoint", "group"]].rename(
        columns={"endpoint": "value"}
    )
    matrix = prepare_plate_matrix(endpoint_tidy)
    assert matrix.shape == (8, 12)

    summary = summarize_by_group(endpoint_tidy, group_columns=["group"])
    assert {"group", "mean", "median", "std", "count"}.issubset(summary.columns)

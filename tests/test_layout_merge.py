import pandas as pd
import pytest

from rosettier.exceptions import MissingWellError, PlateSizeMismatchError
from rosettier.io import parse_timeseries_wide, wide_to_long
from rosettier.layout import load_layout, merge_measurements_with_layout
from rosettier.plates import PlateSpec


def _measurement_long(plate_size: int = 96):
    wells = PlateSpec.from_size(plate_size).canonical_wells()
    df = pd.DataFrame({"time": [0], **{w: [1.0] for w in wells}})
    wide = parse_timeseries_wide(df, plate_size=plate_size)
    return wide_to_long(wide, plate_size=plate_size)


def _layout_df(plate_size: int = 96):
    wells = PlateSpec.from_size(plate_size).canonical_wells()
    return pd.DataFrame({"well": wells, "group": ["g1"] * len(wells)})


def test_load_layout_validates_complete_wells():
    layout = load_layout(_layout_df(96), plate_size=96)
    assert len(layout) == 96


def test_merge_measurements_with_layout_success():
    merged = merge_measurements_with_layout(_measurement_long(96), _layout_df(96), plate_size=96)
    assert "group" in merged.columns
    assert len(merged) == 96


def test_merge_measurements_with_layout_accepts_case_insensitive_layout_wells():
    layout = _layout_df(96).copy()
    layout["well"] = layout["well"].str.lower()
    merged = merge_measurements_with_layout(_measurement_long(96), layout, plate_size=96)
    assert merged["group"].notna().all()


def test_layout_mismatch_missing_well_raises():
    bad = _layout_df(96).iloc[:-1].copy()
    with pytest.raises(MissingWellError):
        load_layout(bad, plate_size=96)


def test_layout_measurement_plate_size_mismatch_raises():
    with pytest.raises(PlateSizeMismatchError):
        merge_measurements_with_layout(_measurement_long(96), _layout_df(384), plate_size=96)


def test_merge_measurements_with_layout_avoids_layout_suffix_collisions():
    measurements = _measurement_long(96).copy()
    wells = PlateSpec.from_size(96).canonical_wells()
    layout = pd.DataFrame(
        {
            "well": wells,
            "time": [0] * len(wells),
            "time_layout": ["meta"] * len(wells),
        }
    )

    merged = merge_measurements_with_layout(measurements, layout, plate_size=96)
    assert "time_layout_1" in merged.columns
    assert "time_layout" in merged.columns


def test_merge_measurements_with_layout_can_accept_measurement_subset_when_requested():
    measurements = pd.DataFrame(
        {
            "well": ["A01", "A02", "B01"],
            "row": ["A", "A", "B"],
            "column": [1, 2, 1],
            "time": [0.0, 0.0, 0.0],
            "value": [1.0, 2.0, 3.0],
        }
    )

    merged = merge_measurements_with_layout(
        measurements,
        _layout_df(96),
        plate_size=96,
        require_complete_measurements=False,
    )

    assert merged["well"].tolist() == ["A01", "A02", "B01"]
    assert merged["group"].tolist() == ["g1", "g1", "g1"]


def test_merge_measurements_with_layout_rejects_subset_by_default():
    measurements = pd.DataFrame({"well": ["A01"], "time": [0.0], "value": [1.0]})

    with pytest.raises(PlateSizeMismatchError):
        merge_measurements_with_layout(measurements, _layout_df(96), plate_size=96)

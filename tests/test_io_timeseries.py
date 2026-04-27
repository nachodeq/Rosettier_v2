import pandas as pd
import pytest

from rosettier.exceptions import DuplicatedTimepointError, MissingWellError, NonNumericMeasurementError
from rosettier.io import parse_endpoint, parse_timeseries_wide, wide_to_long
from rosettier.plates import PlateSpec


def _wide_df(plate_size: int, with_time: bool = True):
    wells = PlateSpec.from_size(plate_size).canonical_wells()
    data = {w: [float(i), float(i + 1)] for i, w in enumerate(wells)}
    df = pd.DataFrame(data)
    if with_time:
        df.insert(0, "time", [0, 1])
    return df


def test_parse_timeseries_wide_96_success():
    df = _wide_df(96)
    parsed = parse_timeseries_wide(df, plate_size=96)
    assert parsed.shape == (2, 97)


def test_parse_timeseries_wide_384_success():
    df = _wide_df(384)
    parsed = parse_timeseries_wide(df, plate_size=384)
    assert parsed.shape == (2, 385)


def test_parse_timeseries_rejects_duplicate_timepoints():
    df = _wide_df(96)
    df["time"] = [0, 0]
    with pytest.raises(DuplicatedTimepointError):
        parse_timeseries_wide(df, plate_size=96)


def test_parse_timeseries_rejects_non_numeric_measurements():
    df = _wide_df(96)
    df["A01"] = df["A01"].astype(object)
    df.loc[0, "A01"] = "bad"
    with pytest.raises(NonNumericMeasurementError):
        parse_timeseries_wide(df, plate_size=96)


def test_endpoint_with_explicit_time_column():
    df = _wide_df(96).iloc[[0]].copy()
    parsed = parse_endpoint(df, plate_size=96)
    assert list(parsed["time"]) == [0]


def test_endpoint_without_time_column_uses_default_time():
    wells = PlateSpec.from_size(96).canonical_wells()
    df = pd.DataFrame([{w: 1.0 for w in wells}])
    parsed = parse_endpoint(df, plate_size=96)
    assert list(parsed["time"]) == [0.0]


def test_endpoint_without_time_column_requires_single_row():
    wells = PlateSpec.from_size(96).canonical_wells()
    df = pd.DataFrame([{w: 1.0 for w in wells}, {w: 2.0 for w in wells}])
    with pytest.raises(DuplicatedTimepointError):
        parse_endpoint(df, plate_size=96)


def test_wide_to_long_works_and_preserves_plate_completeness():
    wide = parse_timeseries_wide(_wide_df(96), plate_size=96)
    long_df = wide_to_long(wide, plate_size=96)
    assert len(long_df) == 96 * 2


def test_wide_to_long_rejects_partial_plate():
    df = _wide_df(96)
    df = df.drop(columns=["A01"])
    with pytest.raises(MissingWellError):
        wide_to_long(df, plate_size=96)

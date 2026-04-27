"""I/O and reshaping helpers for measurement data."""

from __future__ import annotations

import pandas as pd

from .exceptions import DuplicatedTimepointError, NonNumericMeasurementError
from .plates import PlateSpec, infer_plate_size, validate_complete_well_set


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Return a numeric copy of measurement values or raise on non-numeric cells."""
    coerced = df.apply(pd.to_numeric, errors="coerce")
    if coerced.isna().any().any() and not df.isna().equals(coerced.isna()):
        raise NonNumericMeasurementError("Measurements must be numeric")
    return coerced


def parse_timeseries_wide(df: pd.DataFrame, plate_size: int, time_col: str = "time") -> pd.DataFrame:
    """Parse wide time-series data where rows are timepoints and columns are wells.

    Returns:
        A new dataframe containing ``time_col`` and canonical ordered well columns.
    """
    if time_col not in df.columns:
        raise KeyError(f"Missing time column: {time_col}")

    parsed = df.copy()
    if parsed[time_col].duplicated().any():
        raise DuplicatedTimepointError("Timepoints must not be duplicated")

    well_cols = [c for c in parsed.columns if c != time_col]
    normalized = validate_complete_well_set(well_cols, plate_size=plate_size)

    rename_map = dict(zip(well_cols, normalized))
    parsed = parsed.rename(columns=rename_map)

    numeric_values = _coerce_numeric(parsed[normalized])
    out = pd.concat([parsed[[time_col]], numeric_values], axis=1)
    return out[[time_col] + PlateSpec.from_size(plate_size).canonical_wells()]


def parse_endpoint(df: pd.DataFrame, plate_size: int, time_col: str = "time", default_time: float = 0.0) -> pd.DataFrame:
    """Parse endpoint data as a single-row time-series.

    If ``time_col`` is not present, a default timepoint is inserted.
    """
    if time_col in df.columns:
        return parse_timeseries_wide(df, plate_size=plate_size, time_col=time_col)

    endpoint = df.copy()
    if len(endpoint) != 1:
        raise DuplicatedTimepointError("Endpoint input without time column must have exactly one row")

    endpoint.insert(0, time_col, default_time)
    return parse_timeseries_wide(endpoint, plate_size=plate_size, time_col=time_col)


def wide_to_long(
    df: pd.DataFrame,
    plate_size: int,
    time_col: str = "time",
    value_name: str = "value",
) -> pd.DataFrame:
    """Convert validated wide time-series data to tidy/long format."""
    if time_col not in df.columns:
        raise KeyError(f"Missing time column: {time_col}")

    wells = [c for c in df.columns if c != time_col]
    validate_complete_well_set(wells, plate_size=plate_size)

    long_df = df.melt(
        id_vars=[time_col],
        value_vars=PlateSpec.from_size(plate_size).canonical_wells(),
        var_name="well",
        value_name=value_name,
    )
    long_df[value_name] = _coerce_numeric(long_df[[value_name]])[value_name]
    return long_df.sort_values([time_col, "well"]).reset_index(drop=True)


def infer_plate_from_dataframe(df: pd.DataFrame, time_col: str = "time") -> PlateSpec:
    """Infer plate format from well columns in a wide dataframe."""
    wells = [c for c in df.columns if c != time_col]
    return infer_plate_size(wells)

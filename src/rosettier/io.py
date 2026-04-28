"""I/O and reshaping helpers for measurement data."""

from __future__ import annotations

from io import StringIO
import re

import pandas as pd

from .exceptions import DuplicatedTimepointError, NonNumericMeasurementError, PlateSizeMismatchError
from .plates import PlateSpec, infer_plate_size, normalize_well, validate_complete_well_set

_TIME_HMS_PATTERN = re.compile(r"^\s*(?:(\d+):)?(\d+):(\d+(?:[.,]\d+)?)\s*$")


def _resolve_delimiter(delimiter: str) -> str | None:
    options = {"auto": None, "tab": "\t", "comma": ",", "semicolon": ";"}
    if delimiter not in options:
        raise ValueError(f"Unsupported delimiter setting: {delimiter}")
    return options[delimiter]


def _normalize_decimal_text(value: object, decimal: str) -> object:
    if pd.isna(value):
        return value

    text = str(value).strip()
    if text == "":
        return pd.NA

    if decimal == "comma":
        return text.replace(".", "").replace(",", ".")
    if decimal == "point":
        return text.replace(",", "")
    if decimal == "auto":
        has_comma = "," in text
        has_point = "." in text
        if has_comma and has_point:
            last_separator = max(text.rfind(","), text.rfind("."))
            if text[last_separator] == ",":
                return text.replace(".", "").replace(",", ".")
            return text.replace(",", "")
        if has_comma and not has_point:
            return text.replace(",", ".")
        return text

    raise ValueError(f"Unsupported decimal setting: {decimal}")


def _parse_elapsed_minutes(time_series: pd.Series, decimal: str) -> pd.Series:
    parsed_values: list[float] = []
    for raw in time_series:
        if pd.isna(raw):
            raise ValueError("Time column contains missing values.")

        text = str(raw).strip()
        if text == "":
            raise ValueError("Time column contains blank values.")

        hms_match = _TIME_HMS_PATTERN.match(text)
        if hms_match:
            hour_group, minute_group, second_group = hms_match.groups()
            hours = int(hour_group) if hour_group is not None else 0
            minutes = int(minute_group)
            seconds_text = _normalize_decimal_text(second_group, decimal=decimal)
            try:
                seconds = float(seconds_text)  # type: ignore[arg-type]
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Unable to parse time value: {raw!r}") from exc
            parsed_values.append((hours * 60.0) + minutes + (seconds / 60.0))
            continue

        normalized_text = _normalize_decimal_text(text, decimal=decimal)
        try:
            parsed_values.append(float(normalized_text))  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unable to parse time value: {raw!r}") from exc

    elapsed = pd.Series(parsed_values, index=time_series.index, dtype="float64")
    elapsed = elapsed - float(elapsed.iloc[0])
    return elapsed


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


def parse_plate_reader_wide(
    source: pd.DataFrame | str,
    plate_size: int,
    *,
    time_col: str = "Time",
    delimiter: str = "auto",
    decimal: str = "auto",
) -> pd.DataFrame:
    """Parse plate-reader wide tables into canonical tidy format.

    The parser supports 96-well and 384-well column layouts, user-controlled
    delimiter and decimal handling, and deterministic conversion of time values
    into elapsed minutes.
    """
    if isinstance(source, pd.DataFrame):
        raw = source.copy()
    else:
        sep = _resolve_delimiter(delimiter)
        if sep is None:
            raw = pd.read_csv(StringIO(source), sep=None, engine="python", dtype=str)
        else:
            raw = pd.read_csv(StringIO(source), sep=sep, dtype=str)

    if time_col not in raw.columns:
        raise KeyError(f"Missing time column: {time_col}")

    spec = PlateSpec.from_size(plate_size)
    rename_map: dict[str, str] = {}
    well_cols: list[str] = []
    alternate_sizes = [size for size in (96, 384) if size != plate_size]
    alternate_specs = [PlateSpec.from_size(size) for size in alternate_sizes]
    for column in raw.columns:
        if column == time_col:
            continue
        try:
            canonical = normalize_well(str(column), spec=spec)
        except Exception:
            for alternate_spec in alternate_specs:
                try:
                    normalize_well(str(column), spec=alternate_spec)
                except Exception:
                    continue
                raise PlateSizeMismatchError(
                    f"Column {column!r} is invalid for selected {plate_size}-well plate and indicates a "
                    f"{alternate_spec.size}-well layout."
                ) from None
            continue
        rename_map[column] = canonical
        well_cols.append(column)

    validate_complete_well_set([rename_map[col] for col in well_cols], plate_size=plate_size)

    working = raw.rename(columns=rename_map)
    ordered_wells = PlateSpec.from_size(plate_size).canonical_wells()
    well_values = working[ordered_wells].apply(lambda col: col.map(lambda value: _normalize_decimal_text(value, decimal=decimal)))

    try:
        numeric_values = _coerce_numeric(well_values)
    except NonNumericMeasurementError as exc:
        raise NonNumericMeasurementError("Failed to parse measurement values with selected decimal setting.") from exc

    elapsed_minutes = _parse_elapsed_minutes(working[time_col], decimal=decimal)
    if elapsed_minutes.duplicated().any():
        raise DuplicatedTimepointError("Timepoints must not be duplicated after parsing.")

    tidy = pd.concat([elapsed_minutes.rename("time"), numeric_values], axis=1).melt(
        id_vars=["time"],
        value_vars=ordered_wells,
        var_name="well",
        value_name="value",
    )
    tidy["row"] = tidy["well"].str[0]
    tidy["column"] = tidy["well"].str[1:].astype(int)
    tidy = tidy[["well", "row", "column", "time", "value"]]
    return tidy.sort_values(["time", "well"]).reset_index(drop=True)

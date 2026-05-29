"""Neutral export and plot-preparation utilities for Rosettier tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schema import enrich_well_coordinates, normalize_measurement_column, require_columns

_SUPPORTED_EXTENSIONS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".parquet": "parquet",
}
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _escape_spreadsheet_formula(value: object) -> object:
    """Return a spreadsheet-safe string value for delimited text exports."""
    if isinstance(value, str) and value.lstrip().startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def sanitize_for_delimited_export(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with text cells and headers escaped to reduce CSV/TSV formula injection risk."""
    sanitized = df.copy(deep=True)
    for column in sanitized.select_dtypes(include=["object", "string"]).columns:
        sanitized[column] = sanitized[column].map(_escape_spreadsheet_formula)
    sanitized.columns = [_escape_spreadsheet_formula(column) for column in sanitized.columns]
    return sanitized


def dataframe_to_delimited_text(df: pd.DataFrame, *, sep: str = ",") -> str:
    """Serialize a dataframe as CSV/TSV text after spreadsheet-formula escaping."""
    return sanitize_for_delimited_export(df).to_csv(index=False, sep=sep)


def validate_export_path(path: str | Path) -> str:
    """Validate export extension and return the inferred format label."""
    suffix = Path(path).suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported export extension: {suffix or '<none>'}. Allowed: {allowed}")
    return _SUPPORTED_EXTENSIONS[suffix]


def export_table(df: pd.DataFrame, path: str | Path, format: str | None = None) -> None:
    """Export a dataframe to CSV/TSV/Parquet without mutating input."""
    path_obj = Path(path)

    export_format = format.lower() if format is not None else validate_export_path(path_obj)

    if export_format == "csv":
        path_obj.write_text(dataframe_to_delimited_text(df), encoding="utf-8")
        return
    if export_format == "tsv":
        path_obj.write_text(dataframe_to_delimited_text(df, sep="\t"), encoding="utf-8")
        return
    if export_format == "parquet":
        df.copy(deep=True).to_parquet(path_obj, index=False)
        return

    raise ValueError(f"Unsupported export format: {export_format}")


def prepare_plate_matrix(
    df: pd.DataFrame,
    value_column: str = "value",
    aggregation: str | None = None,
) -> pd.DataFrame:
    """Build a plate-shaped matrix from tidy well-level data."""
    if value_column == "value":
        normalized = normalize_measurement_column(df)
        require_columns(normalized, ["well", "value"])
        table = enrich_well_coordinates(normalized)[["well", "row", "column", "value"]].copy()
    else:
        require_columns(df, ["well", "row", "column", value_column])
        table = df[["well", "row", "column", value_column]].copy()

    duplicate_wells = table.duplicated(subset=["well"], keep=False)

    if duplicate_wells.any() and aggregation is None:
        raise ValueError("Multiple values per well found; provide an aggregation argument")

    if aggregation is None:
        matrix = table.pivot(index="row", columns="column", values=value_column)
    else:
        matrix = table.pivot_table(index="row", columns="column", values=value_column, aggfunc=aggregation)

    matrix = matrix.sort_index(axis=0).sort_index(axis=1)
    matrix.columns.name = None
    matrix.index.name = None
    return matrix


def summarize_by_group(
    df: pd.DataFrame,
    group_columns: list[str],
    value_column: str = "value",
    aggregations: tuple[str, ...] = ("mean", "median", "std", "count"),
) -> pd.DataFrame:
    """Compute descriptive grouped summaries only (no tests/inference)."""
    require_columns(df, [*group_columns, value_column])

    summary = (
        df.groupby(group_columns, dropna=False)[value_column]
        .agg(list(aggregations))
        .reset_index()
    )
    return summary

"""Neutral export and plot-preparation utilities for Rosettier tables."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

_SUPPORTED_EXTENSIONS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".parquet": "parquet",
}


def _require_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_export_path(path: str | Path) -> str:
    """Validate export extension and return the inferred format label."""
    suffix = Path(path).suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported export extension: {suffix or '<none>'}. Allowed: {allowed}")
    return _SUPPORTED_EXTENSIONS[suffix]


def export_table(df: pd.DataFrame, path: str | Path, format: str | None = None) -> None:
    """Export a dataframe to CSV/TSV/Parquet without mutating input."""
    out = df.copy(deep=True)
    path_obj = Path(path)

    export_format = format.lower() if format is not None else validate_export_path(path_obj)

    if export_format == "csv":
        out.to_csv(path_obj, index=False)
        return
    if export_format == "tsv":
        out.to_csv(path_obj, index=False, sep="\t")
        return
    if export_format == "parquet":
        out.to_parquet(path_obj, index=False)
        return

    raise ValueError(f"Unsupported export format: {export_format}")


def prepare_plate_matrix(
    df: pd.DataFrame,
    value_column: str = "value",
    aggregation: str | None = None,
) -> pd.DataFrame:
    """Build a plate-shaped matrix from tidy well-level data."""
    _require_columns(df, ["well", "row", "column", value_column])

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
    _require_columns(df, [*group_columns, value_column])

    summary = (
        df.groupby(group_columns, dropna=False)[value_column]
        .agg(list(aggregations))
        .reset_index()
    )
    return summary

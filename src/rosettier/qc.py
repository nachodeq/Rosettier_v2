"""Deterministic quality-control utilities for tidy Rosettier measurements."""

from __future__ import annotations

from typing import Any

import pandas as pd


_REQUIRED_TIDY_COLUMNS = ("well", "row", "column", "time", "value")


def _validate_required_columns(df: pd.DataFrame, required: tuple[str, ...] = _REQUIRED_TIDY_COLUMNS) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def summarize_missing_values(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Summarize missing values overall and per well.

    Returns:
        A dictionary with:
        - ``overall``: one-row DataFrame containing missing and non-missing counts/fractions.
        - ``per_well``: per-well missing and non-missing counts/fractions.
    """
    _validate_required_columns(df)

    values = df["value"]
    total = int(len(values))
    n_missing = int(values.isna().sum())
    n_non_missing = total - n_missing

    overall = pd.DataFrame(
        {
            "n_total": [total],
            "n_missing": [n_missing],
            "n_non_missing": [n_non_missing],
            "fraction_missing": [n_missing / total if total else 0.0],
            "fraction_non_missing": [n_non_missing / total if total else 0.0],
        }
    )

    per_well = (
        df.groupby("well", as_index=False)["value"]
        .agg(n_total="size", n_missing=lambda s: s.isna().sum())
        .assign(
            n_non_missing=lambda d: d["n_total"] - d["n_missing"],
            fraction_missing=lambda d: d["n_missing"] / d["n_total"],
            fraction_non_missing=lambda d: d["n_non_missing"] / d["n_total"],
        )
        .sort_values("well")
        .reset_index(drop=True)
    )

    return {"overall": overall, "per_well": per_well}


def detect_constant_wells(df: pd.DataFrame, min_timepoints: int = 3) -> pd.DataFrame:
    """Flag wells with constant non-missing values across time.

    NaNs are ignored when determining constancy.
    Wells with fewer than ``min_timepoints`` non-missing observations are not flagged.
    """
    _validate_required_columns(df)

    per_well = (
        df.groupby("well", as_index=False)["value"]
        .agg(
            n_non_missing=lambda s: s.notna().sum(),
            n_unique_non_missing=lambda s: s.dropna().nunique(),
        )
        .assign(
            is_constant=lambda d: (d["n_non_missing"] >= min_timepoints)
            & (d["n_unique_non_missing"] == 1)
        )
        .sort_values("well")
        .reset_index(drop=True)
    )

    return per_well


def detect_outlier_wells(df: pd.DataFrame, method: str = "mad", threshold: float = 3.5) -> pd.DataFrame:
    """Detect well-level outliers from median endpoint-like summaries.

    Each well is summarized by its median value before scoring.
    """
    _validate_required_columns(df)

    if method != "mad":
        raise ValueError(f"Unsupported method: {method}")

    summary = (
        df.groupby("well", as_index=False)["value"]
        .median()
        .rename(columns={"value": "summary_value"})
        .sort_values("well")
        .reset_index(drop=True)
    )

    center = float(summary["summary_value"].median())
    mad = float((summary["summary_value"] - center).abs().median())

    if mad == 0.0:
        summary["score"] = 0.0
        summary.loc[summary["summary_value"] != center, "score"] = float("inf")
    else:
        summary["score"] = 0.67448975 * (summary["summary_value"] - center) / mad

    summary["is_outlier"] = summary["score"].abs() > threshold
    return summary[["well", "summary_value", "score", "is_outlier"]]


def detect_edge_effects(df: pd.DataFrame) -> pd.DataFrame:
    """Compare median values between border wells and inner wells."""
    _validate_required_columns(df)

    row_min, row_max = df["row"].min(), df["row"].max()
    col_min, col_max = df["column"].min(), df["column"].max()

    border_mask = (
        (df["row"] == row_min)
        | (df["row"] == row_max)
        | (df["column"] == col_min)
        | (df["column"] == col_max)
    )

    border_values = df.loc[border_mask, "value"]
    inner_values = df.loc[~border_mask, "value"]

    result = pd.DataFrame(
        {
            "n_border": [int(border_values.notna().sum())],
            "n_inner": [int(inner_values.notna().sum())],
            "median_border": [float(border_values.median()) if border_values.notna().any() else float("nan")],
            "median_inner": [float(inner_values.median()) if inner_values.notna().any() else float("nan")],
        }
    )
    result["difference"] = result["median_border"] - result["median_inner"]
    return result


def qc_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Return a combined QC result bundle for a tidy measurement table."""
    _validate_required_columns(df)

    return {
        "missing": summarize_missing_values(df),
        "constant_wells": detect_constant_wells(df),
        "outlier_wells": detect_outlier_wells(df),
        "edge_effects": detect_edge_effects(df),
    }

"""Time-series feature extraction for tidy Rosettier measurements."""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

_REQUIRED_COLUMNS = ("well", "row", "column", "time", "value")


def _validate_required_columns(df: pd.DataFrame) -> None:
    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_no_duplicate_timepoints(df: pd.DataFrame) -> None:
    duplicated = df.duplicated(subset=["well", "time"], keep=False)
    if duplicated.any():
        raise ValueError("Duplicate timepoints detected within at least one well")


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    _validate_required_columns(df)
    _validate_no_duplicate_timepoints(df)
    return df.sort_values(["well", "time"]).copy()


def _well_identity(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values(["well", "time"])
        .groupby("well", as_index=False)
        .agg(row=("row", "first"), column=("column", "first"))
    )


def _per_well_feature(
    df: pd.DataFrame,
    value_name: str,
    fn: Callable[[pd.DataFrame], float],
) -> pd.DataFrame:
    base = _prepare(df)
    feature = pd.DataFrame(
        {
            "well": [well for well, _ in base.groupby("well", sort=True)],
            value_name: [fn(group) for _, group in base.groupby("well", sort=True)],
        }
    )
    return _well_identity(base).merge(feature, on="well", how="left")


def extract_endpoint(df: pd.DataFrame) -> pd.DataFrame:
    """Return final observed non-missing value at maximum time for each well."""

    def endpoint_for_well(group: pd.DataFrame) -> float:
        observed = group.dropna(subset=["value"])
        if observed.empty:
            return float("nan")
        return float(observed.iloc[-1]["value"])

    return _per_well_feature(df, "endpoint", endpoint_for_well)


def extract_auc(df: pd.DataFrame) -> pd.DataFrame:
    """Return AUC per well using trapezoidal integration over non-missing points."""
    trap = getattr(np, "trapezoid", np.trapz)

    def auc_for_well(group: pd.DataFrame) -> float:
        observed = group.dropna(subset=["value"])
        if len(observed) < 2:
            return float("nan")
        return float(trap(observed["value"].to_numpy(), observed["time"].to_numpy()))

    return _per_well_feature(df, "auc", auc_for_well)


def extract_max_slope(df: pd.DataFrame) -> pd.DataFrame:
    """Return maximum finite-difference slope between consecutive timepoints per well."""

    def max_slope_for_well(group: pd.DataFrame) -> float:
        observed = group.dropna(subset=["value"])
        if len(observed) < 2:
            return float("nan")
        dt = np.diff(observed["time"].to_numpy())
        dv = np.diff(observed["value"].to_numpy())
        slopes = dv / dt
        return float(np.max(slopes))

    return _per_well_feature(df, "max_slope", max_slope_for_well)


def extract_time_to_threshold(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Return first time each well reaches value >= threshold, else NaN."""

    def ttt_for_well(group: pd.DataFrame) -> float:
        observed = group.dropna(subset=["value"])
        reached = observed.loc[observed["value"] >= threshold, "time"]
        if reached.empty:
            return float("nan")
        return float(reached.iloc[0])

    return _per_well_feature(df, "time_to_threshold", ttt_for_well)


def extract_features(df: pd.DataFrame, threshold: float | None = None) -> pd.DataFrame:
    """Combine endpoint/AUC/max slope and optional threshold time into one table."""
    base = _prepare(df)

    features = _well_identity(base)
    features = features.merge(extract_endpoint(base)[["well", "endpoint"]], on="well", how="left")
    features = features.merge(extract_auc(base)[["well", "auc"]], on="well", how="left")
    features = features.merge(extract_max_slope(base)[["well", "max_slope"]], on="well", how="left")

    if threshold is not None:
        features = features.merge(
            extract_time_to_threshold(base, threshold=threshold)[["well", "time_to_threshold"]],
            on="well",
            how="left",
        )

    metadata_cols = [c for c in base.columns if c not in _REQUIRED_COLUMNS]
    stable_cols: list[str] = []
    for col in metadata_cols:
        is_constant_within_well = base.groupby("well")[col].nunique(dropna=False).le(1).all()
        if is_constant_within_well:
            stable_cols.append(col)

    if stable_cols:
        metadata = base.groupby("well", as_index=False)[stable_cols].first()
        features = features.merge(metadata, on="well", how="left")

    return features.sort_values("well").reset_index(drop=True)

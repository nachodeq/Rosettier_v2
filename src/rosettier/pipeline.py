"""Deterministic high-level analysis pipeline for Rosettier."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .exceptions import SchemaValidationError
from .features import extract_features as extract_feature_table
from .io import infer_plate_from_dataframe, parse_endpoint, parse_timeseries_wide, wide_to_long
from .layout import merge_measurements_with_layout
from .qc import qc_summary
from .schema import ensure_canonical_tidy, require_columns


def validate_pipeline_inputs(
    measurements_df: pd.DataFrame,
    layout_df: pd.DataFrame | None = None,
    mode: str = "timeseries",
    extract_features: bool = True,
    compute_qc: bool = True,
) -> None:
    """Validate input combinations and user-facing options for ``run_pipeline``."""
    if not isinstance(measurements_df, pd.DataFrame):
        raise SchemaValidationError("measurements_df must be a pandas DataFrame")

    if mode not in {"timeseries", "endpoint"}:
        raise SchemaValidationError("mode must be either 'timeseries' or 'endpoint'")

    if not isinstance(extract_features, bool):
        raise SchemaValidationError("extract_features must be a boolean")

    if not isinstance(compute_qc, bool):
        raise SchemaValidationError("compute_qc must be a boolean")

    if layout_df is not None:
        if not isinstance(layout_df, pd.DataFrame):
            raise SchemaValidationError("layout_df must be a pandas DataFrame when provided")
        require_columns(layout_df, ["well"])


def run_pipeline(
    measurements_df: pd.DataFrame,
    layout_df: pd.DataFrame | None = None,
    mode: str = "timeseries",
    extract_features: bool = True,
    compute_qc: bool = True,
) -> dict[str, Any]:
    """Run a deterministic Rosettier pipeline over wide-format measurements."""
    validate_pipeline_inputs(
        measurements_df=measurements_df,
        layout_df=layout_df,
        mode=mode,
        extract_features=extract_features,
        compute_qc=compute_qc,
    )

    measurement_copy = measurements_df.copy(deep=True)
    layout_copy = layout_df.copy(deep=True) if layout_df is not None else None

    plate_spec = infer_plate_from_dataframe(measurement_copy, time_col="time")

    if mode == "timeseries":
        parsed_wide = parse_timeseries_wide(measurement_copy, plate_size=plate_spec.size, time_col="time")
    else:
        parsed_wide = parse_endpoint(measurement_copy, plate_size=plate_spec.size, time_col="time")

    tidy = wide_to_long(parsed_wide, plate_size=plate_spec.size, time_col="time", value_name="value")
    tidy = ensure_canonical_tidy(tidy)

    if layout_copy is not None:
        tidy = merge_measurements_with_layout(tidy, layout_copy, plate_size=plate_spec.size)
        tidy = ensure_canonical_tidy(tidy)

    tidy = tidy.sort_values(["well", "time"]).reset_index(drop=True)

    qc_results = qc_summary(tidy) if compute_qc else None
    features_df = extract_feature_table(tidy) if extract_features else None

    if features_df is not None:
        features_df = features_df.sort_values(["well"]).reset_index(drop=True)

    return {
        "tidy": tidy,
        "qc": qc_results,
        "features": features_df,
    }

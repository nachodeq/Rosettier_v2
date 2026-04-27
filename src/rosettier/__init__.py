"""Rosettier core package."""

from .exceptions import (
    DuplicatedTimepointError,
    DuplicatedWellError,
    InvalidWellError,
    MissingWellError,
    NonNumericMeasurementError,
    PlateSizeMismatchError,
    RosettierError,
)
from .export import export_table, prepare_plate_matrix, summarize_by_group, validate_export_path
from .features import (
    extract_auc,
    extract_endpoint,
    extract_features,
    extract_max_slope,
    extract_time_to_threshold,
)
from .io import infer_plate_from_dataframe, parse_endpoint, parse_timeseries_wide, wide_to_long
from .layout import load_layout, merge_measurements_with_layout
from .plates import PlateSpec, infer_plate_size, normalize_well, normalize_wells, validate_complete_well_set
from .qc import (
    detect_constant_wells,
    detect_edge_effects,
    detect_outlier_wells,
    qc_summary,
    summarize_missing_values,
)

__all__ = [
    "RosettierError",
    "InvalidWellError",
    "MissingWellError",
    "DuplicatedWellError",
    "NonNumericMeasurementError",
    "DuplicatedTimepointError",
    "PlateSizeMismatchError",
    "PlateSpec",
    "validate_export_path",
    "export_table",
    "prepare_plate_matrix",
    "summarize_by_group",
    "extract_endpoint",
    "extract_auc",
    "extract_max_slope",
    "extract_time_to_threshold",
    "extract_features",
    "normalize_well",
    "normalize_wells",
    "validate_complete_well_set",
    "infer_plate_size",
    "parse_timeseries_wide",
    "parse_endpoint",
    "wide_to_long",
    "infer_plate_from_dataframe",
    "load_layout",
    "merge_measurements_with_layout",
    "summarize_missing_values",
    "detect_constant_wells",
    "detect_outlier_wells",
    "detect_edge_effects",
    "qc_summary",
]

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
from .io import infer_plate_from_dataframe, parse_endpoint, parse_timeseries_wide, wide_to_long
from .layout import load_layout, merge_measurements_with_layout
from .plates import PlateSpec, infer_plate_size, normalize_well, normalize_wells, validate_complete_well_set

__all__ = [
    "RosettierError",
    "InvalidWellError",
    "MissingWellError",
    "DuplicatedWellError",
    "NonNumericMeasurementError",
    "DuplicatedTimepointError",
    "PlateSizeMismatchError",
    "PlateSpec",
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
]

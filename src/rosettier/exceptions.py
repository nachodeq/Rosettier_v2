"""Custom exceptions for Rosettier core package."""


class RosettierError(Exception):
    """Base exception for package errors."""


class InvalidWellError(RosettierError):
    """Raised when one or more well identifiers are malformed or out of range."""


class MissingWellError(RosettierError):
    """Raised when a required well is missing from a complete plate set."""


class DuplicatedWellError(RosettierError):
    """Raised when duplicate well identifiers are found after normalization."""


class NonNumericMeasurementError(RosettierError):
    """Raised when measurement values contain non-numeric data."""


class DuplicatedTimepointError(RosettierError):
    """Raised when duplicate timepoints are present."""


class PlateSizeMismatchError(RosettierError):
    """Raised when wells do not match the expected plate size or between datasets."""

"""Canonical schema utilities for Rosettier tidy measurement tables."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from .exceptions import SchemaValidationError

CANONICAL_TIDY_COLUMNS: tuple[str, ...] = ("well", "row", "column", "time", "value")
_WELL_PATTERN = re.compile(r"^([A-Za-z]+)(\d+)$")


def require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    """Require that ``df`` contains every requested column."""
    required = list(columns)
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SchemaValidationError(f"Missing required columns: {missing}")


def normalize_measurement_column(
    df: pd.DataFrame,
    measurement_column: str = "measurement",
    value_column: str = "value",
) -> pd.DataFrame:
    """Return a copy where legacy ``measurement`` is normalized to canonical ``value``."""
    normalized = df.copy()
    if value_column not in normalized.columns and measurement_column in normalized.columns:
        normalized = normalized.rename(columns={measurement_column: value_column})
    return normalized


def enrich_well_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with canonicalized ``well`` plus ``row`` and ``column`` columns."""
    require_columns(df, ["well"])

    enriched = df.copy()
    parsed = enriched["well"].astype(str).str.strip().str.extract(_WELL_PATTERN)
    if parsed.isna().any().any():
        raise SchemaValidationError("Well identifiers could not be parsed into row/column coordinates")

    row = parsed[0].str.upper()
    column = parsed[1].astype(int)
    enriched["well"] = row + column.map(lambda c: f"{c:02d}")
    enriched["row"] = row
    enriched["column"] = column
    return enriched


def ensure_canonical_tidy(df: pd.DataFrame) -> pd.DataFrame:
    """Return a canonical tidy copy with required columns and normalized naming."""
    canonical = normalize_measurement_column(df)
    require_columns(canonical, ["well", "time", "value"])
    canonical = enrich_well_coordinates(canonical)
    require_columns(canonical, CANONICAL_TIDY_COLUMNS)
    return canonical

"""Plate definitions and strict well validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .exceptions import DuplicatedWellError, InvalidWellError, MissingWellError, PlateSizeMismatchError

_WELL_PATTERN = re.compile(r"^([A-Za-z]+)(\d+)$")


@dataclass(frozen=True)
class PlateSpec:
    """Specification for a supported microtiter plate format.

    Attributes:
        size: Nominal well count (96 or 384).
        rows: Canonical row labels in display order.
        columns: Canonical numeric column labels in display order.
    """

    size: int
    rows: tuple[str, ...]
    columns: tuple[int, ...]

    @classmethod
    def from_size(cls, size: int) -> "PlateSpec":
        """Build a plate specification for a supported plate size."""
        if size == 96:
            return cls(size=96, rows=tuple("ABCDEFGH"), columns=tuple(range(1, 13)))
        if size == 384:
            return cls(size=384, rows=tuple("ABCDEFGHIJKLMNOP"), columns=tuple(range(1, 25)))
        raise PlateSizeMismatchError(f"Unsupported plate size: {size}")

    def canonical_wells(self) -> list[str]:
        """Return wells in canonical row-major order (e.g., ``A01``..``H12``)."""
        width = len(str(max(self.columns)))
        return [f"{row}{col:0{width}d}" for row in self.rows for col in self.columns]


def normalize_well(well: str, spec: PlateSpec) -> str:
    """Normalize and validate a single well identifier for a given plate.

    The function is case-insensitive on input and always returns an uppercase,
    zero-padded canonical representation.
    """
    if not isinstance(well, str):
        raise InvalidWellError(f"Well must be a string: {well!r}")

    stripped = well.strip().upper()
    match = _WELL_PATTERN.match(stripped)
    if not match:
        raise InvalidWellError(f"Invalid well format: {well!r}")

    row, col_text = match.groups()
    if row not in spec.rows:
        raise InvalidWellError(f"Invalid well row for {spec.size}-well plate: {well!r}")

    col = int(col_text)
    if col not in spec.columns:
        raise InvalidWellError(f"Invalid well column for {spec.size}-well plate: {well!r}")

    width = len(str(max(spec.columns)))
    return f"{row}{col:0{width}d}"


def normalize_wells(wells: Iterable[str], spec: PlateSpec) -> list[str]:
    """Normalize and validate many wells.

    Raises:
        DuplicatedWellError: If two or more values collide after normalization.
    """
    normalized = [normalize_well(well, spec=spec) for well in wells]
    if len(set(normalized)) != len(normalized):
        raise DuplicatedWellError("Duplicate wells detected after normalization")
    return normalized


def validate_complete_well_set(wells: Iterable[str], plate_size: int) -> list[str]:
    """Validate that provided wells exactly match a complete selected plate.

    Partial plates are rejected.
    """
    spec = PlateSpec.from_size(plate_size)
    normalized = normalize_wells(wells, spec=spec)
    expected = set(spec.canonical_wells())
    provided = set(normalized)

    if provided != expected:
        if provided.issubset(expected):
            missing = sorted(expected - provided)
            raise MissingWellError(f"Missing wells for {plate_size}-well plate: {missing[:5]}...")
        extra = sorted(provided - expected)
        raise PlateSizeMismatchError(f"Wells do not match {plate_size}-well plate; unexpected: {extra[:5]}...")

    return normalized


def infer_plate_size(wells: Iterable[str]) -> PlateSpec:
    """Infer plate size from a complete set of wells only."""
    raw = list(wells)
    for size in (96, 384):
        spec = PlateSpec.from_size(size)
        try:
            normalized = normalize_wells(raw, spec=spec)
        except (InvalidWellError, DuplicatedWellError):
            continue

        if set(normalized) == set(spec.canonical_wells()):
            return spec

    raise PlateSizeMismatchError("Could not infer plate size from provided wells; must be complete 96 or 384 set")

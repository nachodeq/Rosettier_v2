"""Layout metadata utilities."""

from __future__ import annotations

import pandas as pd

from .exceptions import InvalidWellError, PlateSizeMismatchError
from .plates import PlateSpec, validate_complete_well_set


def load_layout(df: pd.DataFrame, plate_size: int, well_col: str = "well") -> pd.DataFrame:
    """Load and validate layout metadata keyed by well.

    Returns a copy sorted by canonical well name.
    """
    if well_col not in df.columns:
        raise KeyError(f"Missing layout well column: {well_col}")

    layout = df.copy()
    try:
        normalized = validate_complete_well_set(layout[well_col].tolist(), plate_size=plate_size)
    except InvalidWellError as exc:
        raise PlateSizeMismatchError("Layout wells do not match selected plate size") from exc
    layout[well_col] = normalized
    return layout.sort_values(well_col).reset_index(drop=True)


def merge_measurements_with_layout(
    measurements_long: pd.DataFrame,
    layout_df: pd.DataFrame,
    plate_size: int,
    measurement_well_col: str = "well",
    layout_well_col: str = "well",
) -> pd.DataFrame:
    """Merge long measurements with validated layout metadata."""
    if measurement_well_col not in measurements_long.columns:
        raise KeyError(f"Missing measurement well column: {measurement_well_col}")

    if layout_well_col not in layout_df.columns:
        raise KeyError(f"Missing layout well column: {layout_well_col}")

    expected = set(PlateSpec.from_size(plate_size).canonical_wells())
    measurement_wells = set(measurements_long[measurement_well_col].unique())
    normalized_layout = load_layout(layout_df, plate_size=plate_size, well_col=layout_well_col)
    layout_wells = set(normalized_layout[layout_well_col])

    if measurement_wells != expected:
        raise PlateSizeMismatchError("Measurement wells must exactly match selected plate size")
    if layout_wells != expected:
        raise PlateSizeMismatchError("Layout wells must exactly match selected plate size")
    if measurement_wells != layout_wells:
        raise PlateSizeMismatchError("Layout wells must exactly match measurement wells")

    layout_to_merge = normalized_layout.copy()
    overlapping_columns = (
        set(measurements_long.columns).intersection(layout_to_merge.columns) - {layout_well_col}
    )
    rename_map: dict[str, str] = {}
    reserved_names = set(measurements_long.columns).union(layout_to_merge.columns)

    for column in sorted(overlapping_columns):
        candidate = f"{column}_layout"
        suffix_index = 1
        while candidate in reserved_names or candidate in rename_map.values():
            candidate = f"{column}_layout_{suffix_index}"
            suffix_index += 1
        rename_map[column] = candidate

    if rename_map:
        layout_to_merge = layout_to_merge.rename(columns=rename_map)

    return measurements_long.merge(
        layout_to_merge,
        left_on=measurement_well_col,
        right_on=layout_well_col,
        how="left",
    )

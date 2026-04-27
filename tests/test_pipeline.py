import pandas as pd
import pytest

from rosettier.exceptions import SchemaValidationError
from rosettier.pipeline import run_pipeline, validate_pipeline_inputs
from rosettier.plates import PlateSpec


def _timeseries_wide(plate_size: int = 96) -> pd.DataFrame:
    wells = PlateSpec.from_size(plate_size).canonical_wells()
    return pd.DataFrame(
        {
            "time": [0.0, 1.0, 2.0],
            **{well: [float(i), float(i + 1), float(i + 2)] for i, well in enumerate(wells)},
        }
    )


def _endpoint_wide(plate_size: int = 96) -> pd.DataFrame:
    wells = PlateSpec.from_size(plate_size).canonical_wells()
    return pd.DataFrame([{well: float(i) for i, well in enumerate(wells)}])


def _layout(plate_size: int = 96) -> pd.DataFrame:
    wells = PlateSpec.from_size(plate_size).canonical_wells()
    return pd.DataFrame({"well": wells, "group": ["g1" if i % 2 == 0 else "g2" for i in range(len(wells))]})


def test_validate_pipeline_inputs_rejects_invalid_mode():
    with pytest.raises(SchemaValidationError, match="mode must be either"):
        validate_pipeline_inputs(_timeseries_wide(), mode="bad")


def test_run_pipeline_timeseries_with_layout_qc_and_features():
    out = run_pipeline(_timeseries_wide(), layout_df=_layout(), mode="timeseries", extract_features=True, compute_qc=True)

    assert set(out.keys()) == {"tidy", "qc", "features"}
    assert {"well", "row", "column", "time", "value", "group"}.issubset(out["tidy"].columns)
    assert out["qc"] is not None
    assert {"missing", "constant_wells", "outlier_wells", "edge_effects"}.issubset(out["qc"].keys())
    assert out["features"] is not None
    assert {"well", "row", "column", "endpoint", "auc", "max_slope", "group"}.issubset(out["features"].columns)


def test_run_pipeline_endpoint_without_layout_and_optional_outputs_off():
    out = run_pipeline(_endpoint_wide(), mode="endpoint", extract_features=False, compute_qc=False)

    assert out["qc"] is None
    assert out["features"] is None
    assert {"well", "row", "column", "time", "value"}.issubset(out["tidy"].columns)
    assert out["tidy"]["time"].nunique() == 1


def test_run_pipeline_is_deterministic_and_non_mutating():
    measurements = _timeseries_wide()
    layout = _layout()
    measurements_before = measurements.copy(deep=True)
    layout_before = layout.copy(deep=True)

    first = run_pipeline(measurements, layout_df=layout)
    second = run_pipeline(measurements, layout_df=layout)

    pd.testing.assert_frame_equal(first["tidy"], second["tidy"])
    pd.testing.assert_frame_equal(first["features"], second["features"])
    pd.testing.assert_frame_equal(first["qc"]["missing"]["overall"], second["qc"]["missing"]["overall"])
    pd.testing.assert_frame_equal(first["qc"]["missing"]["per_well"], second["qc"]["missing"]["per_well"])
    pd.testing.assert_frame_equal(first["qc"]["constant_wells"], second["qc"]["constant_wells"])
    pd.testing.assert_frame_equal(first["qc"]["outlier_wells"], second["qc"]["outlier_wells"])
    pd.testing.assert_frame_equal(first["qc"]["edge_effects"], second["qc"]["edge_effects"])

    pd.testing.assert_frame_equal(measurements, measurements_before)
    pd.testing.assert_frame_equal(layout, layout_before)


def test_run_pipeline_requires_layout_with_well_column():
    bad_layout = _layout().drop(columns=["well"])
    with pytest.raises(SchemaValidationError, match="Missing required columns"):
        run_pipeline(_timeseries_wide(), layout_df=bad_layout)

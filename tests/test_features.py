import pandas as pd
import pytest
import inspect

from rosettier.features import (
    extract_auc,
    extract_endpoint,
    extract_features,
    extract_max_slope,
    extract_time_to_threshold,
)


def _tidy_df() -> pd.DataFrame:
    rows = [
        ("A01", "A", 1, 0.0, 0.0, "drug", "p1"),
        ("A01", "A", 1, 1.0, 1.0, "drug", "p1"),
        ("A01", "A", 1, 2.0, 2.0, "drug", "p1"),
        ("A02", "A", 2, 0.0, 0.0, "ctrl", "p1"),
        ("A02", "A", 2, 1.0, None, "ctrl", "p1"),
        ("A02", "A", 2, 2.0, 1.0, "ctrl", "p1"),
        ("A03", "A", 3, 0.0, 0.0, "drug", "p2"),
        ("A03", "A", 3, 1.0, 0.0, "drug", "p2"),
        ("A03", "A", 3, 2.0, 0.0, "drug", "p2"),
    ]
    return pd.DataFrame(rows, columns=["well", "row", "column", "time", "value", "condition", "plate_id"])


def test_extract_endpoint_returns_last_non_missing_by_time():
    out = extract_endpoint(_tidy_df()).set_index("well")
    assert out.loc["A01", "endpoint"] == 2.0
    assert out.loc["A02", "endpoint"] == 1.0


def test_extract_auc_handles_nans_and_requires_two_points():
    out = extract_auc(_tidy_df()).set_index("well")
    assert out.loc["A01", "auc"] == 2.0
    assert out.loc["A02", "auc"] == 1.0


def test_extract_max_slope_uses_sorted_time_and_ignores_nans():
    out = extract_max_slope(_tidy_df()).set_index("well")
    assert out.loc["A01", "max_slope"] == 1.0
    assert out.loc["A03", "max_slope"] == 0.0


def test_extract_time_to_threshold_returns_first_crossing_or_nan():
    out = extract_time_to_threshold(_tidy_df(), threshold=1.0).set_index("well")
    assert out.loc["A01", "time_to_threshold"] == 1.0
    assert out.loc["A02", "time_to_threshold"] == 2.0
    assert pd.isna(out.loc["A03", "time_to_threshold"])


def test_extract_features_combines_outputs_and_preserves_stable_metadata():
    out = extract_features(_tidy_df(), threshold=1.0)
    assert {"well", "row", "column", "endpoint", "auc", "max_slope", "time_to_threshold", "condition", "plate_id"}.issubset(
        out.columns
    )
    assert out.set_index("well").loc["A01", "condition"] == "drug"


def test_extract_features_ignores_non_constant_metadata_within_well():
    df = _tidy_df()
    df.loc[df["well"] == "A01", "transient"] = ["x", "y", "z"]
    out = extract_features(df)
    assert "transient" not in out.columns


def test_duplicate_timepoints_within_well_raise_value_error():
    df = pd.concat([_tidy_df(), _tidy_df().iloc[[0]]], ignore_index=True)
    for fn in (extract_endpoint, extract_auc, extract_max_slope, extract_time_to_threshold, extract_features):
        with pytest.raises(ValueError, match="Duplicate timepoints"):
            if fn is extract_time_to_threshold:
                fn(df, threshold=0.5)
            else:
                fn(df)


def test_missing_required_columns_raise_value_error():
    df = _tidy_df().drop(columns=["row"])
    for fn in (extract_endpoint, extract_auc, extract_max_slope, extract_time_to_threshold, extract_features):
        with pytest.raises(ValueError, match="Missing required columns"):
            if fn is extract_time_to_threshold:
                fn(df, threshold=0.5)
            else:
                fn(df)


def test_extract_auc_validates_before_numpy_fallback_resolution(monkeypatch):
    df = _tidy_df().drop(columns=["row"])
    monkeypatch.delattr("rosettier.features.np.trapezoid", raising=False)
    monkeypatch.delattr("rosettier.features.np.trapz", raising=False)
    with pytest.raises(ValueError, match="Missing required columns"):
        extract_auc(df)


def test_extract_auc_uses_internal_fallback_when_numpy_integrators_missing(monkeypatch):
    df = _tidy_df()
    monkeypatch.delattr("rosettier.features.np.trapezoid", raising=False)
    monkeypatch.delattr("rosettier.features.np.trapz", raising=False)
    out = extract_auc(df).set_index("well")
    assert out.loc["A01", "auc"] == 2.0


def test_extract_auc_source_does_not_reference_np_trapz():
    source = inspect.getsource(extract_auc)
    assert "np.trapz" not in source


def test_no_mutation():
    df = _tidy_df()
    before = df.copy(deep=True)

    extract_endpoint(df)
    extract_auc(df)
    extract_max_slope(df)
    extract_time_to_threshold(df, threshold=1.0)
    extract_features(df, threshold=1.0)

    pd.testing.assert_frame_equal(df, before)

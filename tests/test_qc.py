import pandas as pd
import pytest

from rosettier.exceptions import SchemaValidationError


from rosettier.qc import (
    detect_constant_wells,
    detect_edge_effects,
    detect_outlier_wells,
    qc_summary,
    summarize_missing_values,
)


def _tidy_df() -> pd.DataFrame:
    # 3x3 plate-like grid with two timepoints
    rows = [
        ("A01", "A", 1, 0, 1.0),
        ("A01", "A", 1, 1, 1.0),
        ("A02", "A", 2, 0, 1.0),
        ("A02", "A", 2, 1, None),
        ("A03", "A", 3, 0, 1.0),
        ("A03", "A", 3, 1, 1.0),
        ("B01", "B", 1, 0, 1.0),
        ("B01", "B", 1, 1, 1.0),
        ("B02", "B", 2, 0, 1.0),
        ("B02", "B", 2, 1, 10.0),
        ("B03", "B", 3, 0, 1.0),
        ("B03", "B", 3, 1, 1.0),
        ("C01", "C", 1, 0, 1.0),
        ("C01", "C", 1, 1, 1.0),
        ("C02", "C", 2, 0, 1.0),
        ("C02", "C", 2, 1, 1.0),
        ("C03", "C", 3, 0, 1.0),
        ("C03", "C", 3, 1, 1.0),
    ]
    return pd.DataFrame(rows, columns=["well", "row", "column", "time", "value"])


def test_summarize_missing_values_overall_and_per_well():
    df = _tidy_df()
    result = summarize_missing_values(df)

    overall = result["overall"].iloc[0]
    assert overall["n_total"] == 18
    assert overall["n_missing"] == 1

    per_well = result["per_well"].set_index("well")
    assert per_well.loc["A02", "n_missing"] == 1
    assert per_well.loc["A02", "fraction_missing"] == 0.5


def test_detect_constant_wells_ignores_nans_and_respects_min_timepoints():
    df = _tidy_df()
    out = detect_constant_wells(df, min_timepoints=2).set_index("well")
    assert out.loc["A01", "is_constant"]
    assert not out.loc["B02", "is_constant"]
    assert not out.loc["A02", "is_constant"]


def test_detect_outlier_wells_mad_endpoint_like_summary():
    df = _tidy_df()
    out = detect_outlier_wells(df, method="mad", threshold=3.5).set_index("well")
    assert out.loc["B02", "is_outlier"]
    assert out.loc["A01", "score"] == 0.0


def test_detect_edge_effects_returns_expected_summary_fields():
    df = _tidy_df()
    out = detect_edge_effects(df)
    assert list(out.columns) == ["n_border", "n_inner", "median_border", "median_inner", "difference"]
    assert out.iloc[0]["n_inner"] == 2


def test_qc_functions_raise_on_missing_required_columns():
    df = _tidy_df().drop(columns=["well"])
    for fn in (summarize_missing_values, detect_constant_wells, detect_outlier_wells, detect_edge_effects, qc_summary):
        with pytest.raises(SchemaValidationError, match="Missing required columns"):
            fn(df)


def test_qc_functions_do_not_mutate_input_dataframe():
    df = _tidy_df()
    before = df.copy(deep=True)

    summarize_missing_values(df)
    detect_constant_wells(df)
    detect_outlier_wells(df)
    detect_edge_effects(df)
    qc_summary(df)

    pd.testing.assert_frame_equal(df, before)

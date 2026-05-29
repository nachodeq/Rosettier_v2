from pathlib import Path

import pandas as pd
import pytest

from rosettier.export import (
    dataframe_to_delimited_text,
    export_table,
    prepare_plate_matrix,
    sanitize_for_delimited_export,
    summarize_by_group,
    validate_export_path,
)


def _tidy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "well": ["A01", "A02", "B01", "B02"],
            "row": ["A", "A", "B", "B"],
            "column": [1, 2, 1, 2],
            "value": [1.0, 2.0, 3.0, 4.0],
            "group": ["g1", "g1", "g2", "g2"],
        }
    )


def test_validate_export_path_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported export extension"):
        validate_export_path("out.xlsx")


def test_export_table_csv_and_tsv(tmp_path: Path):
    df = _tidy_df()
    before = df.copy(deep=True)

    csv_path = tmp_path / "table.csv"
    tsv_path = tmp_path / "table.tsv"

    export_table(df, csv_path)
    export_table(df, tsv_path)

    loaded_csv = pd.read_csv(csv_path)
    loaded_tsv = pd.read_csv(tsv_path, sep="\t")

    assert loaded_csv.shape == df.shape
    assert loaded_tsv.shape == df.shape
    pd.testing.assert_frame_equal(df, before)


def test_delimited_exports_escape_spreadsheet_formula_text(tmp_path: Path):
    df = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03", "A04", "A05"],
            "metadata": ["=cmd", "+cmd", "-cmd", "@cmd", "safe"],
            "value": [-1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )
    before = df.copy(deep=True)

    sanitized = sanitize_for_delimited_export(df)
    csv_text = dataframe_to_delimited_text(df)
    csv_path = tmp_path / "formula.csv"
    export_table(df, csv_path)

    assert sanitized["metadata"].tolist() == ["'=cmd", "'+cmd", "'-cmd", "'@cmd", "safe"]
    assert sanitized["value"].tolist() == [-1.0, 2.0, 3.0, 4.0, 5.0]
    assert "'=cmd" in csv_text
    assert "'=cmd" in csv_path.read_text(encoding="utf-8")
    pd.testing.assert_frame_equal(df, before)


def test_prepare_plate_matrix_from_tidy_data():
    matrix = prepare_plate_matrix(_tidy_df(), value_column="value")
    assert list(matrix.index) == ["A", "B"]
    assert list(matrix.columns) == [1, 2]
    assert matrix.loc["B", 2] == 4.0


def test_prepare_plate_matrix_duplicate_wells_require_aggregation():
    df = pd.concat([_tidy_df(), _tidy_df().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="provide an aggregation"):
        prepare_plate_matrix(df)

    matrix = prepare_plate_matrix(df, aggregation="mean")
    assert matrix.loc["A", 1] == 1.0


def test_summarize_by_group_descriptive_only():
    out = summarize_by_group(_tidy_df(), group_columns=["group"])
    assert {"group", "mean", "median", "std", "count"}.issubset(out.columns)
    assert set(out["group"]) == {"g1", "g2"}


def test_export_utilities_do_not_mutate_inputs(tmp_path: Path):
    df = _tidy_df()
    before = df.copy(deep=True)

    export_table(df, tmp_path / "x.csv")
    prepare_plate_matrix(df)
    summarize_by_group(df, group_columns=["group"])

    pd.testing.assert_frame_equal(df, before)

import pandas as pd
import pytest
from pathlib import Path

from rosettier.exceptions import DuplicatedTimepointError, MissingWellError, NonNumericMeasurementError, PlateSizeMismatchError
from rosettier.io import parse_endpoint, parse_plate_reader_wide, parse_timeseries_wide, wide_to_long
from rosettier.layout import load_layout, merge_measurements_with_layout
from rosettier.plates import PlateSpec


def _wide_df(plate_size: int, with_time: bool = True):
    wells = PlateSpec.from_size(plate_size).canonical_wells()
    data = {w: [float(i), float(i + 1)] for i, w in enumerate(wells)}
    df = pd.DataFrame(data)
    if with_time:
        df.insert(0, "time", [0, 1])
    return df


def _plate_reader_text(plate_size: int, delimiter: str = "\t", decimal: str = ".") -> str:
    spec = PlateSpec.from_size(plate_size)
    wells = [well.replace("0", "", 1) if well[1] == "0" else well for well in spec.canonical_wells()]
    header = delimiter.join(["Time", *wells])
    row_0_values = []
    row_1_values = []
    for idx, _well in enumerate(wells, start=1):
        base_0 = f"{idx/1000:.3f}"
        base_1 = f"{(idx+1)/1000:.3f}"
        if decimal == ",":
            base_0 = base_0.replace(".", ",")
            base_1 = base_1.replace(".", ",")
        row_0_values.append(base_0)
        row_1_values.append(base_1)

    row_0 = delimiter.join(["0:00:00", *row_0_values])
    row_1 = delimiter.join(["0:10:00", *row_1_values])
    return f"{header}\n{row_0}\n{row_1}\n"


def test_parse_timeseries_wide_96_success():
    df = _wide_df(96)
    parsed = parse_timeseries_wide(df, plate_size=96)
    assert parsed.shape == (2, 97)


def test_parse_timeseries_wide_384_success():
    df = _wide_df(384)
    parsed = parse_timeseries_wide(df, plate_size=384)
    assert parsed.shape == (2, 385)


def test_parse_timeseries_rejects_duplicate_timepoints():
    df = _wide_df(96)
    df["time"] = [0, 0]
    with pytest.raises(DuplicatedTimepointError):
        parse_timeseries_wide(df, plate_size=96)


def test_parse_timeseries_rejects_non_numeric_measurements():
    df = _wide_df(96)
    df["A01"] = df["A01"].astype(object)
    df.loc[0, "A01"] = "bad"
    with pytest.raises(NonNumericMeasurementError):
        parse_timeseries_wide(df, plate_size=96)


def test_endpoint_with_explicit_time_column():
    df = _wide_df(96).iloc[[0]].copy()
    parsed = parse_endpoint(df, plate_size=96)
    assert list(parsed["time"]) == [0]


def test_endpoint_without_time_column_uses_default_time():
    wells = PlateSpec.from_size(96).canonical_wells()
    df = pd.DataFrame([{w: 1.0 for w in wells}])
    parsed = parse_endpoint(df, plate_size=96)
    assert list(parsed["time"]) == [0.0]


def test_endpoint_without_time_column_requires_single_row():
    wells = PlateSpec.from_size(96).canonical_wells()
    df = pd.DataFrame([{w: 1.0 for w in wells}, {w: 2.0 for w in wells}])
    with pytest.raises(DuplicatedTimepointError):
        parse_endpoint(df, plate_size=96)


def test_wide_to_long_works_and_preserves_plate_completeness():
    wide = parse_timeseries_wide(_wide_df(96), plate_size=96)
    long_df = wide_to_long(wide, plate_size=96)
    assert len(long_df) == 96 * 2
    assert "value" in long_df.columns


def test_wide_to_long_supports_legacy_measurement_name():
    wide = parse_timeseries_wide(_wide_df(96), plate_size=96)
    long_df = wide_to_long(wide, plate_size=96, value_name="measurement")
    assert "measurement" in long_df.columns


def test_wide_to_long_rejects_partial_plate():
    df = _wide_df(96)
    df = df.drop(columns=["A01"])
    with pytest.raises(MissingWellError):
        wide_to_long(df, plate_size=96)


def test_parse_plate_reader_wide_96_with_decimal_point_and_comma_delimiter():
    csv_text = _plate_reader_text(96, delimiter=",", decimal=".")
    tidy = parse_plate_reader_wide(
        csv_text,
        plate_size=96,
        time_col="Time",
        delimiter="comma",
        decimal="point",
    )
    assert set(tidy.columns) == {"well", "row", "column", "time", "value"}
    assert tidy["well"].nunique() == 96
    assert tidy["time"].min() == 0.0


def test_parse_plate_reader_wide_384_fixture_handles_decimal_comma_and_ignores_temperature():
    fixture_text = (Path(__file__).parent.parent / "examples" / "384_OD_Measurements.tsv").read_text(encoding="utf-8")
    tidy = parse_plate_reader_wide(
        fixture_text,
        plate_size=384,
        time_col="Time",
        delimiter="tab",
        decimal="comma",
    )
    assert set(tidy.columns) == {"well", "row", "column", "time", "value"}
    assert tidy["well"].nunique() == 384
    assert tidy["time"].iloc[0] == pytest.approx(0.0)
    assert "T" not in tidy["well"].unique()


def test_parse_plate_reader_wide_time_hms_to_elapsed_minutes():
    text = _plate_reader_text(96, delimiter="\t", decimal=",").replace("0:00:00", "0:00:19").replace("0:10:00", "0:10:19")
    tidy = parse_plate_reader_wide(text, plate_size=96, time_col="Time", delimiter="tab", decimal="comma")
    assert sorted(tidy["time"].unique().tolist()) == pytest.approx([0.0, 10.0])


def test_parse_plate_reader_wide_reports_decimal_errors():
    text = _plate_reader_text(96, delimiter="\t", decimal=",")
    text = text.replace("\t0,001\t", "\tbad\t", 1)
    with pytest.raises(NonNumericMeasurementError):
        parse_plate_reader_wide(text, plate_size=96, time_col="Time", delimiter="tab", decimal="comma")


def test_parse_plate_reader_wide_reports_time_errors():
    text = _plate_reader_text(96, delimiter="\t", decimal=",").replace("0:00:00", "not_a_time", 1)
    with pytest.raises(ValueError, match="Unable to parse time value"):
        parse_plate_reader_wide(text, plate_size=96, time_col="Time", delimiter="tab", decimal="comma")


def test_parse_plate_reader_wide_rejects_columns_from_different_plate_format():
    text = _plate_reader_text(96, delimiter="\t", decimal=".")
    lines = text.strip().splitlines()
    lines[0] = f"{lines[0]}\tI1"
    lines[1] = f"{lines[1]}\t0.123"
    lines[2] = f"{lines[2]}\t0.456"

    with pytest.raises(PlateSizeMismatchError, match="384-well"):
        parse_plate_reader_wide("\n".join(lines) + "\n", plate_size=96, time_col="Time", delimiter="tab", decimal="point")


def test_parse_plate_reader_wide_auto_decimal_parses_mixed_separators_eu_style():
    text = _plate_reader_text(96, delimiter="\t", decimal=",")
    text = text.replace("\t0,001\t", "\t1.234,56\t", 1)

    tidy = parse_plate_reader_wide(text, plate_size=96, time_col="Time", delimiter="tab", decimal="auto")
    a01_t0 = tidy[(tidy["well"] == "A01") & (tidy["time"] == 0.0)]["value"].iloc[0]
    assert a01_t0 == pytest.approx(1234.56)


def test_parse_plate_reader_wide_merge_with_layout_metadata_fixture_smoke():
    base = Path(__file__).parent.parent
    measurements_text = (base / "examples" / "384_OD_Measurements.tsv").read_text(encoding="utf-8")
    layout_df = pd.read_csv(base / "examples" / "384_Rosetta.tsv", sep="\t")
    tidy = parse_plate_reader_wide(
        measurements_text,
        plate_size=384,
        time_col="Time",
        delimiter="tab",
        decimal="comma",
    )
    validated_layout = load_layout(layout_df, plate_size=384, well_col="Well")
    merged = merge_measurements_with_layout(tidy, validated_layout, plate_size=384, layout_well_col="Well")
    assert "strain" in merged.columns
    assert merged["well"].nunique() == 384


def test_parse_endpoint_measurements_long_semicolon_with_plate_column():
    from rosettier.io import parse_endpoint_measurements

    spec = PlateSpec.from_size(96)
    rows = ["Well;OD;plate"]
    for idx, well in enumerate(spec.canonical_wells(), start=1):
        rows.append(f"{well};{idx / 1000:.3f};1")

    tidy = parse_endpoint_measurements(
        "\n".join(rows) + "\n",
        plate_size=96,
        value_col="OD",
        delimiter="semicolon",
        decimal="point",
    )

    assert set(["well", "row", "column", "time", "value", "plate"]).issubset(tidy.columns)
    assert tidy["well"].nunique() == 96
    assert tidy["time"].unique().tolist() == [0.0]
    assert tidy.loc[tidy["well"] == "A01", "value"].iloc[0] == pytest.approx(0.001)
    assert tidy.loc[tidy["well"] == "H12", "plate"].iloc[0] == "1"


def test_parse_endpoint_measurements_plate_matrix():
    from rosettier.io import parse_endpoint_measurements

    spec = PlateSpec.from_size(96)
    header = ";" + ";".join(str(col) for col in spec.columns)
    lines = [header]
    for row_idx, row_label in enumerate(spec.rows, start=1):
        values = [f"{(row_idx * col) / 1000:.3f}" for col in spec.columns]
        lines.append(";".join([row_label, *values]))

    tidy = parse_endpoint_measurements("\n".join(lines) + "\n", plate_size=96, delimiter="semicolon", decimal="point")

    assert set(tidy.columns) == {"well", "row", "column", "time", "value"}
    assert tidy["well"].nunique() == 96
    assert tidy.loc[tidy["well"] == "A01", "value"].iloc[0] == pytest.approx(0.001)
    assert tidy.loc[tidy["well"] == "H12", "value"].iloc[0] == pytest.approx(0.096)

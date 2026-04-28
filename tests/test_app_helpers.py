import pandas as pd

from rosettier.plates import PlateSpec
from rosettier_app import app


def test_build_rosetta_table_has_expected_shape_and_columns():
    spec = PlateSpec.from_size(96)
    df = app._build_rosetta_table(spec)
    assert len(df) == 96
    assert list(df.columns) == ["well", "row", "column"]
    assert df.iloc[0]["well"] == "A01"
    assert df.iloc[-1]["well"] == "H12"


def test_ensure_variable_columns_adds_missing_columns():
    base = pd.DataFrame({"well": ["A01"], "row": ["A"], "column": [1]})
    out = app._ensure_variable_columns(base, ["strain", "drug"])
    assert "strain" in out.columns
    assert "drug" in out.columns


def test_assign_value_to_wells_only_updates_selected_wells():
    df = pd.DataFrame(
        {
            "well": ["A01", "A02"],
            "row": ["A", "A"],
            "column": [1, 2],
            "strain": ["", ""],
        }
    )
    out = app._assign_value_to_wells(df, ["A02"], "strain", "WT")
    assert out.loc[out["well"] == "A01", "strain"].iloc[0] == ""
    assert out.loc[out["well"] == "A02", "strain"].iloc[0] == "WT"


def test_selected_wells_from_event_maps_point_indices_to_wells():
    rosetta_df = pd.DataFrame({"well": ["A01", "A02", "A03"]})
    event = {"selection": {"points": [{"point_index": 0}, {"point_index": 2}]}}
    wells = app._selected_wells_from_event(event, rosetta_df)
    assert wells == ["A01", "A03"]


def test_event_contains_selection_payload_distinguishes_no_event_from_empty_selection():
    assert app._event_contains_selection_payload(None) is False
    assert app._event_contains_selection_payload({}) is False
    assert app._event_contains_selection_payload({"selection": {"points": []}}) is True


def test_filter_tidy_by_time_window_applies_bounds_without_mutating_input():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A01", "A01"],
            "row": ["A", "A", "A"],
            "column": [1, 1, 1],
            "time": [0.0, 10.0, 20.0],
            "value": [0.1, 0.2, 0.3],
        }
    )
    out = app._filter_tidy_by_time_window(tidy, enable_time_filter=True, min_time=5.0, max_time=15.0)
    assert list(out["time"]) == [10.0]
    assert list(tidy["time"]) == [0.0, 10.0, 20.0]


def test_compute_selected_features_returns_only_requested_and_renamed_columns():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A01", "A02", "A02"],
            "row": ["A", "A", "A", "A"],
            "column": [1, 1, 2, 2],
            "time": [0.0, 1.0, 0.0, 1.0],
            "value": [0.0, 1.0, 0.5, 0.75],
        }
    )
    out = app._compute_selected_features(
        tidy,
        selected_features=["endpoint", "max_slope"],
        threshold=None,
        signal_name="GFP",
    )
    assert {"well", "row", "column", "GFP_endpoint", "GFP_max_slope"} == set(out.columns)
    assert "GFP_time_to_threshold" not in out.columns


def test_compute_selected_features_requires_threshold_for_time_to_threshold():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A01"],
            "row": ["A", "A"],
            "column": [1, 1],
            "time": [0.0, 1.0],
            "value": [0.0, 1.0],
        }
    )
    try:
        app._compute_selected_features(
            tidy,
            selected_features=["time_to_threshold"],
            threshold=None,
            signal_name="OD",
        )
    except ValueError as exc:
        assert "Threshold must be provided" in str(exc)
    else:  # pragma: no cover - explicit failure branch
        raise AssertionError("Expected ValueError when threshold is missing.")


def test_make_plate_figure_96_is_compact_and_shows_labels_and_variable_hover():
    spec = PlateSpec.from_size(96)
    df = app._build_rosetta_table(spec)
    df["strain"] = ""
    df.loc[df["well"] == "A01", "strain"] = "WT"

    fig = app._make_plate_figure(df, spec, selected_wells=["A01"], color_variable="strain")
    trace = fig.data[0]

    assert trace.mode == "markers+text"
    assert trace.text is not None
    assert "strain: WT" in trace.hovertext[0]
    assert fig.layout.height == 560


def test_make_plate_figure_384_hides_well_labels_to_avoid_overcrowding():
    spec = PlateSpec.from_size(384)
    df = app._build_rosetta_table(spec)

    fig = app._make_plate_figure(df, spec, selected_wells=[], color_variable=None)
    trace = fig.data[0]

    assert trace.mode == "markers"
    assert trace.text is None
    assert "Well: A01" in trace.hovertext[0]


def test_prepare_raw_curve_plot_df_includes_selected_metadata_group():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A01", "A02"],
            "time": [0.0, 10.0, 0.0],
            "value": [0.1, 0.2, 0.05],
        }
    )
    merged = pd.DataFrame(
        {
            "well": ["A01", "A02"],
            "condition": ["drug", "control"],
        }
    )

    out = app._prepare_raw_curve_plot_df(tidy, wells_to_plot=["A01"], merged_df=merged, group_column="condition")

    assert list(out["well"]) == ["A01", "A01"]
    assert list(out["metadata_group"]) == ["drug", "drug"]


def test_prepare_raw_curve_plot_df_defaults_empty_group_when_not_selected():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A02"],
            "time": [5.0, 5.0],
            "value": [0.12, 0.2],
        }
    )

    out = app._prepare_raw_curve_plot_df(tidy, wells_to_plot=["A01", "A02"], merged_df=None, group_column=None)

    assert list(out["well"]) == ["A01", "A02"]
    assert set(out["metadata_group"]) == {""}

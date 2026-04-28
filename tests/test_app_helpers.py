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


def test_event_contains_selection_payload_requires_non_empty_points():
    assert app._event_contains_selection_payload(None) is False
    assert app._event_contains_selection_payload({}) is False
    assert app._event_contains_selection_payload({"selection": {"points": []}}) is False
    assert app._event_contains_selection_payload({"selection": {"points": [{"point_index": 0}]}}) is True


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


def test_prepare_raw_curve_plot_df_includes_selected_metadata_label():
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
    assert list(out["metadata_label"]) == ["drug", "drug"]


def test_prepare_raw_curve_plot_df_defaults_all_wells_label_when_not_selected():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A02"],
            "time": [5.0, 5.0],
            "value": [0.12, 0.2],
        }
    )

    out = app._prepare_raw_curve_plot_df(tidy, wells_to_plot=["A01", "A02"], merged_df=None, group_column=None)

    assert list(out["well"]) == ["A01", "A02"]
    assert set(out["metadata_label"]) == {"All wells"}


def test_prepare_raw_curve_plot_df_is_safe_when_selected_metadata_column_is_missing():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A02"],
            "time": [5.0, 5.0],
            "value": [0.12, 0.2],
        }
    )
    merged = pd.DataFrame({"well": ["A01", "A02"], "condition": ["drug", "control"]})

    out = app._prepare_raw_curve_plot_df(tidy, wells_to_plot=["A01", "A02"], merged_df=merged, group_column="missing")

    assert set(out["metadata_label"]) == {"All wells"}


def test_resolve_raw_curve_group_column_warns_when_selected_column_is_missing():
    merged = pd.DataFrame({"well": ["A01"], "condition": ["drug"]})

    resolved, warning = app._resolve_raw_curve_group_column(merged, "batch")

    assert resolved is None
    assert "unavailable" in str(warning)


def test_rename_value_column_for_signal_uses_signal_name_without_mutating_input():
    tidy = pd.DataFrame({"well": ["A01"], "time": [0.0], "value": [0.1]})
    out = app._rename_value_column_for_signal(tidy, signal_name="GFP")

    assert "GFP" in out.columns
    assert "value" not in out.columns
    assert "value" in tidy.columns


def test_metadata_color_value_map_assigns_deterministic_colors():
    plot_df = pd.DataFrame({"metadata_label": ["drug", "control", "drug"]})

    color_map = app._metadata_color_value_map(plot_df, metadata_column="metadata_label")

    assert set(color_map) == {"control", "drug"}
    assert color_map["control"] != color_map["drug"]


def test_filter_selected_wells_keeps_all_when_selection_is_empty():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03"],
            "time": [0.0, 0.0, 0.0],
            "value": [0.1, 0.2, 0.3],
        }
    )
    out = app._filter_selected_wells(tidy, selected_wells=[])
    assert sorted(out["well"].unique().tolist()) == ["A01", "A02", "A03"]


def test_filter_selected_wells_applies_plate_selection():
    tidy = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03"],
            "time": [0.0, 0.0, 0.0],
            "value": [0.1, 0.2, 0.3],
        }
    )
    out = app._filter_selected_wells(tidy, selected_wells=["A02"])
    assert out["well"].tolist() == ["A02"]


def test_resolve_feature_column_prefers_signal_prefixed_name():
    features = pd.DataFrame({"well": ["A01"], "OD_auc": [1.23], "auc": [9.99]})
    assert app._resolve_feature_column(features, "OD", "auc") == "OD_auc"


def test_prepare_feature_comparison_table_preserves_well_level_replicates():
    features = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03"],
            "OD_auc": [1.0, 2.0, 3.0],
        }
    )
    merged = pd.DataFrame(
        {
            "well": ["A01", "A01", "A02", "A03"],
            "time": [0.0, 1.0, 0.0, 0.0],
            "strain": ["WT", "WT", "WT", "KO"],
            "RTecnica": ["r1", "r1", "r2", "r1"],
        }
    )

    out, missing_count = app._prepare_feature_comparison_table(
        features_df=features,
        merged_df=merged,
        feature_column="OD_auc",
        group_columns=["strain"],
        color_column="RTecnica",
        facet_column=None,
    )

    assert len(out) == 3
    assert sorted(out["well"].tolist()) == ["A01", "A02", "A03"]
    assert missing_count == {"strain": 0}


def test_prepare_feature_comparison_table_counts_missing_group_labels():
    features = pd.DataFrame({"well": ["A01", "A02"], "OD_endpoint": [0.2, 0.3]})
    merged = pd.DataFrame(
        {
            "well": ["A01", "A02"],
            "time": [0.0, 0.0],
            "strain": ["WT", None],
        }
    )

    out, missing_count = app._prepare_feature_comparison_table(
        features_df=features,
        merged_df=merged,
        feature_column="OD_endpoint",
        group_columns=["strain"],
    )

    assert len(out) == 2
    assert missing_count == {"strain": 1}


def test_combine_qc_outputs_for_export_includes_component_labels():
    qc = {
        "missing": {
            "overall": pd.DataFrame({"n_total": [2], "n_missing": [1]}),
            "per_well": pd.DataFrame({"well": ["A01"], "n_missing": [1]}),
        },
        "constant_wells": pd.DataFrame({"well": ["A01"], "is_constant": [True]}),
        "outlier_wells": pd.DataFrame({"well": ["A02"], "is_outlier": [False]}),
        "edge_effects": pd.DataFrame({"difference": [0.1]}),
    }

    out = app._combine_qc_outputs_for_export(qc)

    assert "qc_component" in out.columns
    assert "qc_scope" in out.columns
    assert {"missing_values", "constant_wells", "outlier_wells", "edge_effects"} <= set(out["qc_component"])


def test_build_group_label_column_supports_multiple_group_columns():
    comparison = pd.DataFrame(
        {
            "well": ["A01", "A02"],
            "strain": ["WT", "KO"],
            "drug": ["none", "drugA"],
        }
    )

    out = app._build_group_label_column(comparison, ["strain", "drug"])

    assert out.tolist() == ["strain=WT | drug=none", "strain=KO | drug=drugA"]


def test_comparison_plot_mode_uses_points_for_single_sample():
    comparison = pd.DataFrame({"well": ["A01"]})
    assert app._comparison_plot_mode(comparison) == "points"


def test_comparison_plot_mode_uses_box_for_two_or_more_samples():
    comparison = pd.DataFrame({"well": ["A01", "A02"]})
    assert app._comparison_plot_mode(comparison) == "box"

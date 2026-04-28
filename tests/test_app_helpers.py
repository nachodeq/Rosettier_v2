import json
from io import BytesIO
import zipfile

import pandas as pd
import pytest

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
        selected_features=["endpoint", "max_slope", "max_value"],
        threshold=None,
        signal_name="GFP",
    )
    assert {"well", "row", "column", "GFP_endpoint", "GFP_max_slope", "GFP_max_value"} == set(out.columns)
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

    assert out.tolist() == ["WT | none", "KO | drugA"]


def test_comparison_plot_mode_uses_points_for_single_sample():
    comparison = pd.DataFrame({"well": ["A01"]})
    assert app._comparison_plot_mode(comparison) == "points"


def test_comparison_plot_mode_uses_points_when_all_groups_are_singletons():
    comparison = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03"],
            "__compare_group_label__": ["WT", "KO", "mut"],
        }
    )
    assert app._comparison_plot_mode(comparison) == "points"


def test_comparison_plot_mode_uses_box_when_any_group_has_replicates():
    comparison = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03"],
            "__compare_group_label__": ["WT", "WT", "KO"],
        }
    )
    assert app._comparison_plot_mode(comparison) == "points"


def test_comparison_plot_mode_uses_box_when_any_group_has_more_than_two_points():
    comparison = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03", "A04"],
            "__compare_group_label__": ["WT", "WT", "WT", "KO"],
        }
    )
    assert app._comparison_plot_mode(comparison) == "box"


def test_build_feature_comparison_figure_returns_plotly_figure():
    comparison = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03", "A04"],
            "strain": ["WT", "WT", "KO", "KO"],
            "feature_auc": [1.0, 2.0, 3.0, 4.0],
        }
    )

    fig, plot_df = app._build_feature_comparison_figure(
        comparison_df=comparison,
        group_columns=["strain"],
        feature_column="feature_auc",
        feature_label="AUC",
        signal_name="OD",
        feature_name="auc",
        color_column=None,
        facet_column=None,
    )

    assert fig.__class__.__name__ == "Figure"
    assert "__compare_group_label__" in plot_df.columns


def test_build_feature_comparison_figure_includes_color_column_legend_entries():
    comparison = pd.DataFrame(
        {
            "well": ["A01", "A02", "A03", "A04"],
            "strain": ["WT", "WT", "KO", "KO"],
            "replicate": ["r1", "r2", "r1", "r2"],
            "feature_auc": [1.0, 2.0, 3.0, 4.0],
        }
    )

    fig, _ = app._build_feature_comparison_figure(
        comparison_df=comparison,
        group_columns=["strain"],
        feature_column="feature_auc",
        feature_label="AUC",
        signal_name="OD",
        feature_name="auc",
        color_column="replicate",
        facet_column=None,
    )

    trace_names = {str(getattr(trace, "name", "")) for trace in fig.data}
    assert "r1" in trace_names
    assert "r2" in trace_names


def test_plotly_image_bytes_uses_requested_format():
    class DummyFigure:
        def to_image(self, **kwargs):
            assert kwargs["format"] == "png"
            return b"png-bytes"

    image_bytes = app._plotly_image_bytes(DummyFigure(), image_format="png")
    assert image_bytes == b"png-bytes"


def test_render_plot_download_buttons_renders_png_and_svg_buttons():
    calls: list[dict] = []

    class DummyFigure:
        def to_image(self, **kwargs):
            fmt = kwargs["format"]
            return f"{fmt}-bytes".encode("utf-8")

    class DummySt:
        def download_button(self, **kwargs):
            calls.append(kwargs)

    app._render_plot_download_buttons(
        DummySt(),
        fig=DummyFigure(),
        filename_stem="my_plot",
        key_prefix="plot",
    )

    assert len(calls) == 2
    assert calls[0]["label"] == "Download plot (PNG)"
    assert calls[0]["file_name"] == "my_plot.png"
    assert calls[1]["label"] == "Download plot (SVG)"
    assert calls[1]["file_name"] == "my_plot.svg"


def test_comparison_signal_options_disambiguate_duplicate_signal_names():
    options, option_map = app._comparison_signal_options(
        [
            {"signal_name": "OD", "signal_slug": "od_a"},
            {"signal_name": "OD", "signal_slug": "od_b"},
            {"signal_name": "GFP", "signal_slug": "gfp_a"},
        ]
    )

    assert len(options) == 3
    assert option_map[options[0]]["label"] == "OD"
    assert option_map[options[1]]["label"] == "OD (2)"
    assert option_map[options[2]]["label"] == "GFP"


def test_build_feature_ratio_table_computes_per_well_ratio():
    numerator_signal = {
        "signal_name": "DO",
        "features_df": pd.DataFrame({"well": ["A01", "A02"], "DO_endpoint": [0.8, 0.6]}),
        "merged_df": pd.DataFrame({"well": ["A01", "A02"], "strain": ["WT", "KO"], "time": [0.0, 0.0], "value": [0.8, 0.6]}),
    }
    denominator_signal = {
        "signal_name": "GFP",
        "features_df": pd.DataFrame({"well": ["A01", "A02"], "GFP_endpoint": [0.4, 0.3]}),
        "merged_df": None,
    }

    ratio_df, ratio_column, feature_label, signal_label = app._build_feature_ratio_table(
        numerator_signal=numerator_signal,
        denominator_signal=denominator_signal,
        feature_name="endpoint",
    )

    assert ratio_column == "DO_over_GFP_endpoint"
    assert feature_label == "Endpoint (DO/GFP)"
    assert signal_label == "DO/GFP"
    assert ratio_df["well"].tolist() == ["A01", "A02"]
    assert ratio_df[ratio_column].tolist() == [2.0, 2.0]


def test_build_analysis_bundle_zip_includes_manifest_and_signal_exports():
    signal_results = [
        {
            "signal_name": "OD",
            "signal_slug": "OD",
            "tidy_df": pd.DataFrame({"well": ["A01"], "time": [0.0], "OD": [0.1]}),
            "merged_df": pd.DataFrame({"well": ["A01"], "time": [0.0], "OD": [0.1], "strain": ["WT"]}),
            "features_df": pd.DataFrame({"well": ["A01"], "row": ["A"], "column": [1], "OD_auc": [1.23]}),
            "qc_export_df": pd.DataFrame({"qc_component": ["missing_values"], "qc_scope": ["overall"]}),
            "raw_curve_fig": None,
        }
    ]

    bundle_bytes = app._build_analysis_bundle_zip(
        signal_results=signal_results,
        plate_size=96,
        config={"enable_time_filter": True, "min_time": 0.0, "max_time": 120.0, "selected_features": ["auc"]},
        comparison_df=None,
        comparison_name=None,
        comparison_fig=None,
    )

    with zipfile.ZipFile(BytesIO(bundle_bytes), mode="r") as bundle:
        names = set(bundle.namelist())
        assert "signals/OD/parsed_tidy.csv" in names
        assert "signals/OD/merged.csv" in names
        assert "signals/OD/features.csv" in names
        assert "signals/OD/qc_summary.csv" in names
        assert "manifest.json" in names
        manifest = json.loads(bundle.read("manifest.json").decode("utf-8"))
        assert manifest["signal_names"] == ["OD"]
        assert manifest["plate_size"] == 96
        assert manifest["time_filtering"]["enabled"] is True
        assert manifest["selected_features"] == ["auc"]
        assert "timestamp" in manifest


def test_build_analysis_bundle_zip_includes_comparison_table_and_plots_when_available():
    class DummyFigure:
        def to_image(self, **kwargs):
            return f"{kwargs['format']}-bytes".encode("utf-8")

    bundle_bytes = app._build_analysis_bundle_zip(
        signal_results=[
            {
                "signal_name": "OD",
                "signal_slug": "OD",
                "tidy_df": pd.DataFrame({"well": ["A01"]}),
                "merged_df": None,
                "features_df": pd.DataFrame({"well": ["A01"], "row": ["A"], "column": [1], "OD_auc": [1.23]}),
                "qc_export_df": None,
                "raw_curve_fig": DummyFigure(),
            }
        ],
        plate_size=96,
        config={},
        comparison_df=pd.DataFrame({"well": ["A01"], "OD_auc": [1.23]}),
        comparison_name="compare_od_auc",
        comparison_fig=DummyFigure(),
    )

    with zipfile.ZipFile(BytesIO(bundle_bytes), mode="r") as bundle:
        names = set(bundle.namelist())
        assert "signals/OD/raw_curves_plot.png" in names
        assert "signals/OD/raw_curves_plot.svg" in names
        assert "comparison/compare_od_auc.csv" in names
        assert "comparison/comparison_plot.png" in names
        assert "comparison/comparison_plot.svg" in names


def test_build_analysis_bundle_zip_disambiguates_duplicate_signal_slugs():
    signal_results = [
        {
            "signal_name": "OD",
            "signal_slug": "OD",
            "tidy_df": pd.DataFrame({"well": ["A01"], "time": [0.0], "OD": [0.1]}),
            "merged_df": None,
            "features_df": None,
            "qc_export_df": None,
            "raw_curve_fig": None,
        },
        {
            "signal_name": "OD",
            "signal_slug": "OD",
            "tidy_df": pd.DataFrame({"well": ["A02"], "time": [0.0], "OD": [0.2]}),
            "merged_df": None,
            "features_df": None,
            "qc_export_df": None,
            "raw_curve_fig": None,
        },
    ]

    bundle_bytes = app._build_analysis_bundle_zip(
        signal_results=signal_results,
        plate_size=96,
        config={},
        comparison_df=None,
        comparison_name=None,
        comparison_fig=None,
    )

    with zipfile.ZipFile(BytesIO(bundle_bytes), mode="r") as bundle:
        names = set(bundle.namelist())
        assert "signals/OD_1/parsed_tidy.csv" in names
        assert "signals/OD_2/parsed_tidy.csv" in names

"""Streamlit shell for Rosettier v2 local app."""

from __future__ import annotations

from io import StringIO

import pandas as pd

from rosettier.features import extract_features
from rosettier.io import parse_endpoint, parse_timeseries_wide, wide_to_long
from rosettier.layout import load_layout, merge_measurements_with_layout
from rosettier.plates import PlateSpec, validate_complete_well_set
from rosettier.qc import qc_summary


def _read_uploaded_table(uploaded_file) -> pd.DataFrame:
    """Read CSV/TSV uploads without mutating app state."""
    suffix = uploaded_file.name.lower()
    text = uploaded_file.getvalue().decode("utf-8")

    if suffix.endswith(".tsv"):
        return pd.read_csv(StringIO(text), sep="\t")
    return pd.read_csv(StringIO(text))


def _build_rosetta_table(spec: PlateSpec) -> pd.DataFrame:
    """Build base Rosetta table with canonical well coordinates."""
    rows: list[dict[str, object]] = []
    for row in spec.rows:
        for col in spec.columns:
            rows.append({"well": f"{row}{col:02d}", "row": row, "column": col})
    return pd.DataFrame(rows)


def _ordered_rosetta_columns(df: pd.DataFrame) -> list[str]:
    """Return Rosetta columns in canonical order plus user-defined columns."""
    base = ["well", "row", "column"]
    dynamic = [c for c in df.columns if c not in base]
    return [*base, *dynamic]


def _ensure_variable_columns(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    """Return dataframe with all requested variable columns present."""
    out = df.copy()
    for var in variables:
        if var not in out.columns:
            out[var] = ""
    return out[_ordered_rosetta_columns(out)]


def _assign_value_to_wells(
    rosetta_df: pd.DataFrame,
    wells: list[str],
    variable: str,
    value: str,
) -> pd.DataFrame:
    """Return a copy with ``variable=value`` assigned to selected wells."""
    out = rosetta_df.copy()
    if variable not in out.columns:
        out[variable] = ""
    if not wells:
        return out[_ordered_rosetta_columns(out)]
    out.loc[out["well"].isin(wells), variable] = value
    return out[_ordered_rosetta_columns(out)]


def _make_plate_figure(rosetta_df: pd.DataFrame, spec: PlateSpec, selected_wells: list[str], color_variable: str | None):
    """Create a Plotly plate figure for interactive well selection."""
    import plotly.graph_objects as go

    plot_df = rosetta_df[["well", "row", "column"]].copy()
    row_to_y = {row: len(spec.rows) - idx for idx, row in enumerate(spec.rows)}
    plot_df["x"] = plot_df["column"]
    plot_df["y"] = plot_df["row"].map(row_to_y)

    is_selected = plot_df["well"].isin(selected_wells)

    if color_variable is not None and color_variable in rosetta_df.columns:
        color_series = rosetta_df[color_variable].fillna("").astype(str)
        has_value = color_series.str.len() > 0
        colors = ["#4c78a8" if hv else "#d9d9d9" for hv in has_value]
    else:
        colors = ["#d9d9d9"] * len(plot_df)

    marker_sizes = [16 if spec.size == 384 else 28] * len(plot_df)
    line_colors = ["#ff7f0e" if sel else "#b3b3b3" for sel in is_selected]
    line_widths = [2.3 if sel else 0.8 for sel in is_selected]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=plot_df["x"],
                y=plot_df["y"],
                mode="markers+text" if spec.size == 96 else "markers",
                text=plot_df["well"] if spec.size == 96 else None,
                textposition="middle center",
                textfont={"size": 9, "color": "#222222"},
                customdata=plot_df[["well"]],
                marker={
                    "size": marker_sizes,
                    "color": colors,
                    "line": {"color": line_colors, "width": line_widths},
                },
                hovertemplate="Well: %{customdata[0]}<extra></extra>",
            )
        ]
    )

    fig.update_xaxes(
        range=[0.5, len(spec.columns) + 0.5],
        dtick=1,
        title="column",
        showgrid=False,
        zeroline=False,
    )
    fig.update_yaxes(
        range=[0.5, len(spec.rows) + 0.5],
        dtick=1,
        tickmode="array",
        tickvals=list(range(len(spec.rows), 0, -1)),
        ticktext=list(spec.rows),
        title="row",
        showgrid=False,
        zeroline=False,
    )
    fig.update_layout(
        height=650 if spec.size == 96 else 820,
        clickmode="event+select",
        dragmode="select",
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 24, "r": 24, "t": 24, "b": 24},
    )
    return fig


def _selected_wells_from_event(event: dict | None, rosetta_df: pd.DataFrame) -> list[str]:
    """Extract selected wells from streamlit plotly selection payload."""
    if not event:
        return []
    selection = event.get("selection")
    if not selection:
        return []
    points = selection.get("points") or []
    if not points:
        return []

    wells: list[str] = []
    for point in points:
        point_index = point.get("point_index")
        if point_index is None:
            continue
        if 0 <= point_index < len(rosetta_df):
            wells.append(str(rosetta_df.iloc[point_index]["well"]))
    return wells


def _init_rosetta_state(st, plate_size: int) -> None:
    """Initialize stable session state for Create Rosetta mode."""
    if "rosetta_variables" not in st.session_state:
        st.session_state["rosetta_variables"] = []

    if "rosetta_plate_size" not in st.session_state:
        st.session_state["rosetta_plate_size"] = plate_size

    reset_required = "rosetta_df" not in st.session_state or st.session_state["rosetta_plate_size"] != plate_size

    if reset_required:
        spec = PlateSpec.from_size(plate_size)
        rosetta_df = _build_rosetta_table(spec)
        rosetta_df = _ensure_variable_columns(rosetta_df, st.session_state["rosetta_variables"])
        st.session_state["rosetta_df"] = rosetta_df
        st.session_state["rosetta_selected_wells"] = []
        st.session_state["rosetta_plate_size"] = plate_size


def _render_create_rosetta(st, plate_size: int) -> None:
    """Mode: create and export Rosetta metadata."""
    st.header("Create Rosetta")
    _init_rosetta_state(st, plate_size)

    rosetta_df = st.session_state["rosetta_df"]
    variables = st.session_state["rosetta_variables"]
    selected_wells = st.session_state.get("rosetta_selected_wells", [])
    spec = PlateSpec.from_size(plate_size)

    st.subheader("Rosetta editor")

    # A. Visualization variable
    viz_options = ["None", *variables]
    selected_viz_label = st.selectbox("A. Select visualization variable", options=viz_options, index=0)
    selected_viz = None if selected_viz_label == "None" else selected_viz_label

    # B. Interactive plate
    fig = _make_plate_figure(rosetta_df, spec, selected_wells, color_variable=selected_viz)
    event = st.plotly_chart(fig, use_container_width=True, key="rosetta_plate", on_select="rerun")
    just_selected = _selected_wells_from_event(event, rosetta_df)
    if just_selected:
        st.session_state["rosetta_selected_wells"] = sorted(set(just_selected))
        selected_wells = st.session_state["rosetta_selected_wells"]

    st.caption(f"Selected wells ({len(selected_wells)}): {', '.join(selected_wells[:12])}{' ...' if len(selected_wells) > 12 else ''}")
    if st.button("Clear selected wells"):
        st.session_state["rosetta_selected_wells"] = []
        st.rerun()

    # C. Add variable
    new_var = st.text_input("C. Add variable", placeholder="e.g. strain")
    if st.button("Add variable") and new_var.strip():
        candidate = new_var.strip()
        if candidate not in variables:
            st.session_state["rosetta_variables"] = [*variables, candidate]
            st.session_state["rosetta_df"] = _ensure_variable_columns(rosetta_df, st.session_state["rosetta_variables"])
            st.success(f"Added variable: {candidate}")
            st.rerun()
        else:
            st.info(f"Variable already exists: {candidate}")

    # D. Assign values
    if not st.session_state["rosetta_variables"]:
        st.info("D. Assign value to selected wells: add at least one variable first.")
    else:
        assign_variable = st.selectbox(
            "D. Variable to assign",
            options=st.session_state["rosetta_variables"],
            key="assign_variable",
        )
        assign_value = st.text_input("D. Value", key="assign_value", placeholder="e.g. WT")
        if st.button("Assign value to selected wells"):
            st.session_state["rosetta_df"] = _assign_value_to_wells(
                st.session_state["rosetta_df"],
                st.session_state.get("rosetta_selected_wells", []),
                assign_variable,
                assign_value,
            )
            st.success(f"Assigned value to {len(st.session_state.get('rosetta_selected_wells', []))} selected wells.")
            st.rerun()

    st.subheader("Current Rosetta table")
    table_to_show = st.session_state["rosetta_df"][_ordered_rosetta_columns(st.session_state["rosetta_df"])]
    st.dataframe(table_to_show, use_container_width=True, height=320)

    st.subheader("Validate Rosetta")
    try:
        validate_complete_well_set(table_to_show["well"].tolist(), plate_size=plate_size)
        st.success("Rosetta validation passed: well set matches selected plate size.")
    except Exception as exc:  # pragma: no cover - defensive streamlit display
        st.error(f"Rosetta validation failed: {exc}")

    st.subheader("Export Rosetta")
    st.download_button(
        label="Download Rosetta (CSV)",
        data=table_to_show.to_csv(index=False),
        file_name=f"rosetta_layout_{plate_size}.csv",
        mime="text/csv",
    )
    st.download_button(
        label="Download Rosetta (TSV)",
        data=table_to_show.to_csv(index=False, sep="\t"),
        file_name=f"rosetta_layout_{plate_size}.tsv",
        mime="text/tab-separated-values",
    )


def _render_analyze_data(st, plate_size: int) -> None:
    """Mode: validate, parse, QC and feature placeholders."""
    st.header("Analyze Data")

    session_rosetta_available = "rosetta_df" in st.session_state

    st.subheader("1. Upload measurements")
    measurement_file = st.file_uploader(
        "Measurements file (CSV/TSV; wide format: rows=timepoints, columns=wells)",
        type=["csv", "tsv"],
        key="measurements_upload",
    )

    st.subheader("2. Rosetta source")
    rosetta_source = st.radio(
        "Choose Rosetta source",
        options=["Use current session Rosetta", "Upload existing Rosetta CSV/TSV"],
    )
    if rosetta_source == "Use current session Rosetta" and not session_rosetta_available:
        st.info("No Rosetta exists in this session yet. Switch to Create Rosetta mode or upload a Rosetta file.")

    layout_file = None
    if rosetta_source == "Upload existing Rosetta CSV/TSV":
        layout_file = st.file_uploader(
            "Upload Rosetta/layout file (CSV/TSV; keyed by `well`)",
            type=["csv", "tsv"],
            key="layout_upload",
        )

    parsed_wide: pd.DataFrame | None = None
    tidy_df: pd.DataFrame | None = None
    features_df: pd.DataFrame | None = None

    st.subheader("3. Validate and parse")
    if measurement_file is None:
        st.info("Upload measurements to run validation and parsing.")
    else:
        measurements_df = _read_uploaded_table(measurement_file)
        parse_mode = st.selectbox("Input mode", options=["timeseries", "endpoint"], key="analysis_mode")

        try:
            if parse_mode == "timeseries":
                parsed_wide = parse_timeseries_wide(measurements_df, plate_size=plate_size, time_col="time")
            else:
                parsed_wide = parse_endpoint(measurements_df, plate_size=plate_size, time_col="time")

            tidy_df = wide_to_long(parsed_wide, plate_size=plate_size, time_col="time", value_name="value")
            st.success("Measurements validated and parsed to canonical tidy format.")
            st.dataframe(tidy_df.head(12), use_container_width=True)
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to parse measurements: {exc}")

    if tidy_df is not None:
        if rosetta_source == "Use current session Rosetta" and session_rosetta_available:
            layout_df = st.session_state["rosetta_df"].copy()
        elif rosetta_source == "Upload existing Rosetta CSV/TSV" and layout_file is not None:
            layout_df = _read_uploaded_table(layout_file)
        else:
            layout_df = None

        if layout_df is not None:
            try:
                validated_layout = load_layout(layout_df, plate_size=plate_size, well_col="well")
                tidy_df = merge_measurements_with_layout(tidy_df, validated_layout, plate_size=plate_size)
                st.success("Rosetta/layout validated and merged.")
            except Exception as exc:  # pragma: no cover - defensive streamlit display
                st.error(f"Failed to validate/merge Rosetta layout: {exc}")

    st.subheader("4. QC summary")
    if tidy_df is None:
        st.info("QC summary will appear after successful parsing.")
    else:
        try:
            qc = qc_summary(tidy_df)
            overall = qc["missing"]["overall"]
            st.dataframe(overall, use_container_width=True)
            st.caption("Placeholder preview of `qc_summary` output.")
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to compute QC summary: {exc}")

    st.subheader("5. Feature extraction")
    if tidy_df is None:
        st.info("Feature extraction results will appear after successful parsing.")
    else:
        try:
            features_df = extract_features(tidy_df)
            st.dataframe(features_df.head(12), use_container_width=True)
            st.caption("Placeholder preview of endpoint/AUC/max_slope outputs.")
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to extract features: {exc}")

    st.subheader("6. Results / Export")
    if tidy_df is None:
        st.info("Results/export placeholders will activate after parsing.")
        return

    st.caption("Download parsed tidy measurements and (if available) extracted features.")
    st.download_button(
        label="Download tidy (CSV)",
        data=tidy_df.to_csv(index=False),
        file_name="rosettier_tidy.csv",
        mime="text/csv",
    )

    if features_df is not None:
        st.download_button(
            label="Download features (CSV)",
            data=features_df.to_csv(index=False),
            file_name="rosettier_features.csv",
            mime="text/csv",
        )


def main() -> None:
    """Render the Rosettier v2 Streamlit shell."""
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover - tested via import-only tests
        raise RuntimeError(
            "Streamlit is not installed. Install app dependencies with: pip install -e '.[app]'"
        ) from exc

    st.set_page_config(page_title="Rosettier v2", page_icon="🧪", layout="wide")

    st.title("Rosettier v2")
    st.caption("App shell with two modes. Core scientific logic remains in `rosettier` modules.")

    st.sidebar.header("Settings")
    plate_size = st.sidebar.selectbox("Plate size", options=[96, 384], index=0)
    mode = st.sidebar.selectbox("Mode", options=["Create Rosetta", "Analyze Data"], index=0)

    if mode == "Create Rosetta":
        _render_create_rosetta(st, plate_size=plate_size)
    else:
        _render_analyze_data(st, plate_size=plate_size)


if __name__ == "__main__":
    main()

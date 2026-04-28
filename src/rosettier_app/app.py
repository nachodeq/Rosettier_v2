"""Streamlit shell for Rosettier v2 local app."""

from __future__ import annotations

from io import StringIO

import pandas as pd

from rosettier.features import extract_auc, extract_endpoint, extract_max_slope, extract_time_to_threshold
from rosettier.io import parse_plate_reader_wide
from rosettier.layout import load_layout, merge_measurements_with_layout
from rosettier.plates import PlateSpec, validate_complete_well_set
from rosettier.qc import qc_summary


def _read_uploaded_table(uploaded_file) -> pd.DataFrame:
    """Read CSV/TSV uploads without mutating app state."""
    text = uploaded_file.getvalue().decode("utf-8")
    return pd.read_csv(StringIO(text), sep=None, engine="python")


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


def _copy_rosetta_editor_plate_state(st, source_prefix: str, destination_prefix: str, destination_widget_prefix: str) -> None:
    """Copy one plate editor's Rosetta state to another editor without mutating source state."""
    source_df_key = f"{source_prefix}_df"
    source_variables_key = f"{source_prefix}_variables"
    source_selected_key = f"{source_prefix}_selected_wells"

    destination_df_key = f"{destination_prefix}_df"
    destination_variables_key = f"{destination_prefix}_variables"
    destination_selected_key = f"{destination_prefix}_selected_wells"

    if source_df_key not in st.session_state:
        raise KeyError(f"Source plate state not initialized: {source_prefix}")

    source_df = st.session_state[source_df_key].copy(deep=True)
    inferred_source_variables = [c for c in source_df.columns if c not in {"well", "row", "column"}]
    source_variables = list(st.session_state.get(source_variables_key, inferred_source_variables))
    source_selected_wells = list(st.session_state.get(source_selected_key, []))

    st.session_state[destination_df_key] = source_df
    st.session_state[destination_variables_key] = source_variables
    st.session_state[destination_selected_key] = source_selected_wells

    # Reset destination widget selections that depend on variables/options.
    st.session_state.pop(f"{destination_widget_prefix}_viz", None)
    st.session_state.pop(f"{destination_widget_prefix}_assign_variable", None)


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
        hover_text = [
            f"Well: {well}<br>{color_variable}: {value if value != '' else '—'}"
            for well, value in zip(plot_df["well"], color_series, strict=False)
        ]
    else:
        colors = ["#d9d9d9"] * len(plot_df)
        hover_text = [f"Well: {well}" for well in plot_df["well"]]

    marker_size = 15 if spec.size == 384 else 40
    text_size = 7 if spec.size == 384 else 10
    line_colors = ["#ff7f0e" if sel else "#111111" for sel in is_selected]
    line_widths = [2.2 if sel else (0.5 if spec.size == 384 else 0.8) for sel in is_selected]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=plot_df["x"],
                y=plot_df["y"],
                mode="markers+text" if spec.size == 96 else "markers",
                text=plot_df["well"] if spec.size == 96 else None,
                textposition="middle center",
                textfont={"size": text_size, "color": "#111111"},
                customdata=plot_df[["well"]],
                marker={
                    "size": marker_size,
                    "color": colors,
                    "opacity": 0.95,
                    "line": {"color": line_colors, "width": line_widths},
                },
                hovertext=hover_text,
                hovertemplate="%{hovertext}<extra></extra>",
            )
        ]
    )

    fig.update_xaxes(
        range=[0.5, len(spec.columns) + 0.5],
        dtick=1,
        title="Column",
        tickfont={"size": 11},
        title_font={"size": 12},
        showgrid=False,
        zeroline=False,
    )
    fig.update_yaxes(
        range=[0.5, len(spec.rows) + 0.5],
        dtick=1,
        tickmode="array",
        tickvals=list(range(len(spec.rows), 0, -1)),
        ticktext=list(spec.rows),
        title="Row",
        tickfont={"size": 11},
        title_font={"size": 12},
        showgrid=False,
        zeroline=False,
    )
    fig.update_layout(
        height=560 if spec.size == 96 else 700,
        clickmode="event+select",
        dragmode="select",
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
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


def _event_contains_selection_payload(event: dict | None) -> bool:
    """Return whether event includes a selection payload (including empty selection)."""
    return bool(event and ("selection" in event))


def _init_rosetta_state(st, plate_size: int) -> None:
    """Initialize stable session state for Create Rosetta mode."""
    _init_rosetta_editor_state(st, state_prefix="rosetta", plate_size=plate_size)


def _init_rosetta_editor_state(st, state_prefix: str, plate_size: int) -> None:
    """Initialize stable editor state for any Rosetta editor instance."""
    variables_key = f"{state_prefix}_variables"
    plate_size_key = f"{state_prefix}_plate_size"
    df_key = f"{state_prefix}_df"
    selected_wells_key = f"{state_prefix}_selected_wells"

    if variables_key not in st.session_state:
        st.session_state[variables_key] = []

    if plate_size_key not in st.session_state:
        st.session_state[plate_size_key] = plate_size

    reset_required = df_key not in st.session_state or st.session_state[plate_size_key] != plate_size

    if reset_required:
        spec = PlateSpec.from_size(plate_size)
        rosetta_df = _build_rosetta_table(spec)
        rosetta_df = _ensure_variable_columns(rosetta_df, st.session_state[variables_key])
        st.session_state[df_key] = rosetta_df
        st.session_state[selected_wells_key] = []
        st.session_state[plate_size_key] = plate_size


def _map_96_well_to_384_well(well: str, row_offset: int, col_offset: int) -> tuple[str, str, int]:
    """Map one 96-well coordinate onto a 384-well coordinate via legacy offsets."""
    row_label = str(well[0])
    col_label = int(well[1:])
    row_index = ord(row_label) - ord("A")
    mapped_row = chr(ord("A") + (2 * row_index) + row_offset)
    mapped_column = (2 * col_label) - 1 + col_offset
    mapped_well = f"{mapped_row}{mapped_column:02d}"
    return mapped_well, mapped_row, mapped_column


def _combine_four_96_rosettas(rosetta_tables: list[pd.DataFrame]) -> pd.DataFrame:
    """Combine four 96-well Rosettas into one 384-well Rosetta via legacy mapping."""
    if len(rosetta_tables) != 4:
        raise ValueError("Exactly four 96-well Rosetta tables are required.")

    combined_rows: list[dict[str, object]] = []
    offsets = [(0, 0), (0, 1), (1, 0), (1, 1)]

    for idx, rosetta_df in enumerate(rosetta_tables):
        validate_complete_well_set(rosetta_df["well"].tolist(), plate_size=96)
        row_offset, col_offset = offsets[idx]
        metadata_columns = [c for c in rosetta_df.columns if c not in {"well", "row", "column"}]
        for record in rosetta_df.to_dict(orient="records"):
            mapped_well, mapped_row, mapped_col = _map_96_well_to_384_well(
                str(record["well"]), row_offset=row_offset, col_offset=col_offset
            )
            combined_record: dict[str, object] = {"well": mapped_well, "row": mapped_row, "column": mapped_col}
            for metadata_column in metadata_columns:
                combined_record[metadata_column] = record.get(metadata_column)
            combined_rows.append(combined_record)

    combined_df = pd.DataFrame(combined_rows)
    combined_df = _ensure_variable_columns(combined_df, [c for c in combined_df.columns if c not in {"well", "row", "column"}])
    combined_df = combined_df.sort_values(by=["row", "column"], kind="stable").reset_index(drop=True)
    validate_complete_well_set(combined_df["well"].tolist(), plate_size=384)
    return combined_df[_ordered_rosetta_columns(combined_df)]


def _render_rosetta_editor(
    st,
    plate_size: int,
    state_prefix: str,
    widget_prefix: str,
    show_table: bool = True,
    copy_sources: list[tuple[str, str]] | None = None,
) -> pd.DataFrame:
    """Render a reusable Rosetta editor and return its current table."""
    _init_rosetta_editor_state(st, state_prefix=state_prefix, plate_size=plate_size)

    df_key = f"{state_prefix}_df"
    variables_key = f"{state_prefix}_variables"
    selected_key = f"{state_prefix}_selected_wells"

    rosetta_df = st.session_state[df_key]
    variables = st.session_state[variables_key]
    selected_wells = st.session_state.get(selected_key, [])
    spec = PlateSpec.from_size(plate_size)

    if copy_sources:
        source_labels = [label for label, _ in copy_sources]
        selected_source_label = st.selectbox(
            "Copy full plate setup from",
            options=source_labels,
            key=f"{widget_prefix}_copy_source",
        )
        selected_source_prefix = dict(copy_sources)[selected_source_label]
        if st.button(f"Copy from {selected_source_label}", key=f"{widget_prefix}_copy_button"):
            _copy_rosetta_editor_plate_state(
                st,
                source_prefix=selected_source_prefix,
                destination_prefix=state_prefix,
                destination_widget_prefix=widget_prefix,
            )
            st.success(f"Copied full Rosetta setup from {selected_source_label}.")
            st.rerun()

    viz_options = ["None", *variables]
    selected_viz_label = st.selectbox(
        "A. Select visualization variable",
        options=viz_options,
        index=0,
        key=f"{widget_prefix}_viz",
    )
    selected_viz = None if selected_viz_label == "None" else selected_viz_label

    fig = _make_plate_figure(rosetta_df, spec, selected_wells, color_variable=selected_viz)
    event = st.plotly_chart(fig, use_container_width=True, key=f"{widget_prefix}_plate", on_select="rerun")
    just_selected = _selected_wells_from_event(event, rosetta_df)
    if _event_contains_selection_payload(event):
        st.session_state[selected_key] = sorted(set(just_selected))
        selected_wells = st.session_state[selected_key]

    st.caption(f"Selected wells ({len(selected_wells)}): {', '.join(selected_wells[:12])}{' ...' if len(selected_wells) > 12 else ''}")
    if st.button("Clear selected wells", key=f"{widget_prefix}_clear"):
        st.session_state[selected_key] = []
        st.rerun()

    new_var = st.text_input("C. Add variable", placeholder="e.g. strain", key=f"{widget_prefix}_new_var")
    if st.button("Add variable", key=f"{widget_prefix}_add_var") and new_var.strip():
        candidate = new_var.strip()
        if candidate not in variables:
            st.session_state[variables_key] = [*variables, candidate]
            st.session_state[df_key] = _ensure_variable_columns(rosetta_df, st.session_state[variables_key])
            st.success(f"Added variable: {candidate}")
            st.rerun()
        else:
            st.info(f"Variable already exists: {candidate}")

    if not st.session_state[variables_key]:
        st.info("D. Assign value to selected wells: add at least one variable first.")
    else:
        assign_variable = st.selectbox(
            "D. Variable to assign",
            options=st.session_state[variables_key],
            key=f"{widget_prefix}_assign_variable",
        )
        assign_value = st.text_input("D. Value", key=f"{widget_prefix}_assign_value", placeholder="e.g. WT")
        if st.button("Assign value to selected wells", key=f"{widget_prefix}_assign"):
            st.session_state[df_key] = _assign_value_to_wells(
                st.session_state[df_key],
                st.session_state.get(selected_key, []),
                assign_variable,
                assign_value,
            )
            st.success(f"Assigned value to {len(st.session_state.get(selected_key, []))} selected wells.")
            st.rerun()

    table_to_show = st.session_state[df_key][_ordered_rosetta_columns(st.session_state[df_key])]
    if show_table:
        st.subheader("Current Rosetta table")
        st.dataframe(table_to_show, use_container_width=True, height=320)
    return table_to_show


def _render_create_rosetta(st, plate_size: int) -> None:
    """Mode: create and export Rosetta metadata."""
    st.header("Create Rosetta")
    creation_mode = st.radio(
        "Creation mode",
        options=["Direct plate creation", "Combine four 96-well Rosettas into 384"],
        key="create_mode",
    )

    if creation_mode == "Direct plate creation":
        st.subheader("Rosetta editor")
        table_to_show = _render_rosetta_editor(st, plate_size=plate_size, state_prefix="rosetta", widget_prefix="direct")
        st.session_state["rosetta_df"] = table_to_show

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
        return

    st.caption(
        "Important note: when combining four 96-well plates into one 384-well Rosetta, "
        "A1 of the 384-well plate corresponds to A1 from Plate 1, A2 corresponds to A1 from Plate 2, "
        "B1 corresponds to A1 from Plate 3, and B2 corresponds to A1 from Plate 4. "
        "The same interleaving pattern is applied across the entire plate."
    )
    tab_labels = ["Plate 1 (96)", "Plate 2 (96)", "Plate 3 (96)", "Plate 4 (96)"]
    tabs = st.tabs(tab_labels)
    for idx, tab in enumerate(tabs, start=1):
        with tab:
            st.subheader(f"Rosetta editor for Plate {idx}")
            copy_sources = [
                (f"Plate {source_idx}", f"combine_plate_{source_idx}")
                for source_idx in range(1, 5)
                if source_idx != idx
            ]
            _render_rosetta_editor(
                st,
                plate_size=96,
                state_prefix=f"combine_plate_{idx}",
                widget_prefix=f"combine_plate_{idx}",
                copy_sources=copy_sources,
            )

    if st.button("Combine into 384 Rosetta", key="combine_rosettas_384"):
        try:
            combined_df = _combine_four_96_rosettas(
                [st.session_state[f"combine_plate_{idx}_df"] for idx in range(1, 5)]
            )
            st.session_state["combined_384_df"] = combined_df
            st.session_state["rosetta_df"] = combined_df
            st.success("Combined 384 Rosetta created successfully.")
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to combine 96-well Rosettas: {exc}")

    if "combined_384_df" not in st.session_state:
        st.info("Create/edit all four 96-well Rosettas, then click 'Combine into 384 Rosetta'.")
        return

    combined_df = st.session_state["combined_384_df"][_ordered_rosetta_columns(st.session_state["combined_384_df"])]
    st.subheader("Combined 384 Rosetta preview")
    st.dataframe(combined_df, use_container_width=True, height=360)

    st.subheader("Validate combined 384 Rosetta")
    try:
        validate_complete_well_set(combined_df["well"].tolist(), plate_size=384)
        st.success("Combined Rosetta validation passed: complete 384 well set.")
    except Exception as exc:  # pragma: no cover - defensive streamlit display
        st.error(f"Combined Rosetta validation failed: {exc}")

    st.subheader("Export combined 384 Rosetta")
    st.download_button(
        label="Download combined 384 Rosetta (CSV)",
        data=combined_df.to_csv(index=False),
        file_name="rosetta_layout_384_combined.csv",
        mime="text/csv",
    )
    st.download_button(
        label="Download combined 384 Rosetta (TSV)",
        data=combined_df.to_csv(index=False, sep="\t"),
        file_name="rosetta_layout_384_combined.tsv",
        mime="text/tab-separated-values",
    )


_FEATURE_LABELS = {
    "endpoint": "Endpoint",
    "auc": "AUC",
    "max_slope": "Max slope",
    "time_to_threshold": "Time to threshold",
}


def _filter_tidy_by_time_window(
    tidy_df: pd.DataFrame,
    *,
    enable_time_filter: bool,
    min_time: float | None,
    max_time: float | None,
) -> pd.DataFrame:
    """Return a filtered tidy table without mutating the input dataframe."""
    out = tidy_df.copy()
    if not enable_time_filter:
        return out
    if min_time is not None:
        out = out.loc[out["time"] >= float(min_time)]
    if max_time is not None:
        out = out.loc[out["time"] <= float(max_time)]
    return out.reset_index(drop=True)


def _metadata_columns_for_raw_curves(merged_df: pd.DataFrame | None) -> list[str]:
    """Return metadata columns that can annotate raw curve traces."""
    if merged_df is None:
        return []
    reserved = {"well", "row", "column", "time", "value"}
    return [column for column in merged_df.columns if column not in reserved]


def _prepare_raw_curve_plot_df(
    tidy_df: pd.DataFrame,
    wells_to_plot: list[str],
    merged_df: pd.DataFrame | None = None,
    group_column: str | None = None,
) -> pd.DataFrame:
    """Build plot-ready dataframe for raw per-well time-series curves."""
    plot_df = tidy_df.loc[tidy_df["well"].isin(wells_to_plot), ["well", "time", "value"]].copy()

    if merged_df is not None and group_column and group_column in merged_df.columns:
        group_lookup = (
            merged_df[["well", group_column]]
            .dropna(subset=["well"])
            .drop_duplicates(subset=["well"], keep="first")
            .rename(columns={group_column: "metadata_group"})
        )
        plot_df = plot_df.merge(group_lookup, on="well", how="left")
        plot_df["metadata_group"] = plot_df["metadata_group"].fillna("—").astype(str)
    else:
        plot_df["metadata_group"] = ""

    return plot_df.sort_values(["well", "time"]).reset_index(drop=True)


def _compute_selected_features(
    feature_source: pd.DataFrame,
    *,
    selected_features: list[str],
    threshold: float | None,
    signal_name: str,
) -> pd.DataFrame:
    """Compute selected feature set and rename feature columns with signal name."""
    if not selected_features:
        return pd.DataFrame(columns=["well", "row", "column"])

    frames: list[pd.DataFrame] = []
    for feature in selected_features:
        if feature == "endpoint":
            frames.append(extract_endpoint(feature_source)[["well", "endpoint"]])
        elif feature == "auc":
            frames.append(extract_auc(feature_source)[["well", "auc"]])
        elif feature == "max_slope":
            frames.append(extract_max_slope(feature_source)[["well", "max_slope"]])
        elif feature == "time_to_threshold":
            if threshold is None:
                raise ValueError("Threshold must be provided when selecting time to threshold.")
            frames.append(extract_time_to_threshold(feature_source, threshold=threshold)[["well", "time_to_threshold"]])
        else:  # pragma: no cover - defensive guard for UI options
            raise ValueError(f"Unsupported feature selection: {feature}")

    feature_table = feature_source[["well", "row", "column"]].drop_duplicates().sort_values("well")
    for frame in frames:
        feature_table = feature_table.merge(frame, on="well", how="left")

    normalized_signal_name = str(signal_name).strip() or "OD"
    rename_map = {feature: f"{normalized_signal_name}_{feature}" for feature in selected_features}
    return feature_table.rename(columns=rename_map).reset_index(drop=True)


def _render_analyze_data(st, plate_size: int) -> None:
    """Mode: validate, parse, configure analysis, QC, and feature exports."""
    st.header("Analyze Data")

    if "analyze_results" not in st.session_state:
        st.session_state["analyze_results"] = {}

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
        key="analyze_rosetta_source",
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

    delimiter_choice = st.selectbox("Delimiter", options=["auto", "tab", "comma", "semicolon"], index=0, key="analyze_delimiter")
    decimal_choice = st.selectbox("Decimal separator", options=["auto", "comma", "point"], index=0, key="analyze_decimal")
    time_column_name = st.text_input("Time column name", value="Time", key="analyze_time_column")

    st.subheader("3. Analysis setup")
    signal_name = st.text_input("Signal name", value="OD", help="Examples: OD, GFP, RFP, luminescence.", key="analyze_signal_name")
    enable_time_filter = st.checkbox("Enable time filtering", value=False, key="analyze_enable_time_filter")
    min_time = st.number_input("Min time (minutes)", value=0.0, step=1.0, key="analyze_min_time")
    max_time = st.number_input("Max time (minutes)", value=0.0, step=1.0, key="analyze_max_time")
    selected_features = st.multiselect(
        "Features to compute",
        options=["endpoint", "auc", "max_slope", "time_to_threshold"],
        default=["endpoint", "auc", "max_slope"],
        format_func=lambda x: _FEATURE_LABELS.get(x, x),
        key="analyze_selected_features",
    )
    threshold: float | None = None
    if "time_to_threshold" in selected_features:
        threshold = float(st.number_input("Threshold (for time to threshold)", value=0.5, step=0.1, key="analyze_threshold"))

    run_analysis = st.button("Run analysis", type="primary", key="analyze_run_button")
    if run_analysis:
        if measurement_file is None:
            st.info("Upload measurements to run validation and parsing.")
        elif enable_time_filter and min_time > max_time:
            st.error("Time filter is enabled, but min time is greater than max time.")
        elif "time_to_threshold" in selected_features and threshold is None:
            st.error("Provide a threshold when selecting time to threshold.")
        else:
            layout_df: pd.DataFrame | None
            if rosetta_source == "Use current session Rosetta" and session_rosetta_available:
                layout_df = st.session_state["rosetta_df"].copy()
            elif rosetta_source == "Upload existing Rosetta CSV/TSV" and layout_file is not None:
                layout_df = _read_uploaded_table(layout_file)
            else:
                layout_df = None

            sanitized_signal_name = signal_name.strip() or "OD"
            layout_well_column = None
            if layout_df is not None:
                layout_well_column = "well" if "well" in layout_df.columns else "Well"

            config = {
                "signal_name": sanitized_signal_name,
                "enable_time_filter": enable_time_filter,
                "min_time": float(min_time),
                "max_time": float(max_time),
                "selected_features": selected_features,
                "threshold": threshold,
            }

            st.session_state["analyze_results"] = {"config": config}

            measurement_text = measurement_file.getvalue().decode("utf-8")
            st.session_state["analyze_results"]["measurement_text"] = measurement_text
            st.session_state["analyze_results"]["layout_df"] = layout_df
            st.session_state["analyze_results"]["layout_well_column"] = layout_well_column
            st.session_state["analyze_results"]["errors"] = []

    results = st.session_state["analyze_results"]

    tidy_df: pd.DataFrame | None = None
    filtered_tidy_df: pd.DataFrame | None = None
    merged_df: pd.DataFrame | None = None
    features_df: pd.DataFrame | None = None
    qc: dict | None = None
    config = results.get("config")

    st.subheader("4. Validate and parse")
    if "measurement_text" not in results:
        st.info("Configure analysis setup and click 'Run analysis'.")
    else:
        try:
            tidy_df = parse_plate_reader_wide(
                results["measurement_text"],
                plate_size=plate_size,
                time_col=time_column_name,
                delimiter=delimiter_choice,
                decimal=decimal_choice,
            )
            filtered_tidy_df = _filter_tidy_by_time_window(
                tidy_df,
                enable_time_filter=bool(config.get("enable_time_filter")) if config else False,
                min_time=config.get("min_time") if config else None,
                max_time=config.get("max_time") if config else None,
            )
            st.success("Measurements validated and parsed to canonical tidy format.")
            st.caption(f"Preview only (first 12 rows) of {len(tidy_df)} parsed rows.")
            st.dataframe(tidy_df.head(12), use_container_width=True)
            st.write(
                f"Parsed summary: {len(tidy_df)} rows, {tidy_df['well'].nunique()} wells, "
                f"{tidy_df['time'].nunique()} timepoints, time range {tidy_df['time'].min()} to {tidy_df['time'].max()} minutes."
            )
            if config:
                st.write(
                    f"Selected analysis range: {config['min_time']} to {config['max_time']} minutes "
                    f"(filter {'enabled' if config['enable_time_filter'] else 'disabled'})."
                )
            st.write(
                f"Rows/timepoints after selection: {len(filtered_tidy_df)} rows, "
                f"{filtered_tidy_df['time'].nunique()} timepoints."
            )
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to parse measurements: {exc}")

    if filtered_tidy_df is not None:
        layout_df = results.get("layout_df")
        layout_well_column = results.get("layout_well_column")
        if layout_df is not None:
            try:
                validated_layout = load_layout(layout_df, plate_size=plate_size, well_col=layout_well_column)
                merged_df = merge_measurements_with_layout(
                    filtered_tidy_df,
                    validated_layout,
                    plate_size=plate_size,
                    layout_well_col=layout_well_column,
                )
                st.success("Rosetta/layout validated and merged.")
                st.caption(f"Merged preview only (first 12 rows) of {len(merged_df)} rows.")
                st.dataframe(merged_df.head(12), use_container_width=True)
            except Exception as exc:  # pragma: no cover - defensive streamlit display
                st.error(f"Failed to validate/merge Rosetta layout: {exc}")

    st.subheader("5. QC summary")
    if filtered_tidy_df is None:
        st.info("QC summary will appear after successful parsing.")
    else:
        try:
            qc = qc_summary(filtered_tidy_df)
            overall = qc["missing"]["overall"]
            st.dataframe(overall, use_container_width=True)
            st.dataframe(qc["constant_wells"].head(12), use_container_width=True)
            st.dataframe(qc["outlier_wells"].head(12), use_container_width=True)
            st.dataframe(qc["edge_effects"], use_container_width=True)
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to compute QC summary: {exc}")

    st.subheader("6. Feature extraction")
    if filtered_tidy_df is None:
        st.info("Feature extraction results will appear after successful parsing.")
    else:
        try:
            feature_source = merged_df if merged_df is not None else filtered_tidy_df
            features_df = _compute_selected_features(
                feature_source,
                selected_features=config.get("selected_features", []) if config else [],
                threshold=config.get("threshold") if config else None,
                signal_name=config.get("signal_name", "OD") if config else "OD",
            )
            st.write(f"Signal: **{config.get('signal_name', 'OD') if config else 'OD'}**")
            if features_df.shape[1] == 3:
                st.info("No features selected.")
            else:
                st.dataframe(features_df.head(12), use_container_width=True)
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to extract features: {exc}")

    st.subheader("7. Raw curves")
    if filtered_tidy_df is None:
        st.info("Raw curves will appear after successful parsing.")
    else:
        import plotly.express as px

        available_wells = sorted(filtered_tidy_df["well"].dropna().astype(str).unique().tolist())
        selected_wells = st.multiselect(
            "Wells to plot",
            options=available_wells,
            default=[],
            key="analyze_raw_curve_wells",
            help="Leave empty to plot all wells.",
        )
        wells_to_plot = selected_wells if selected_wells else available_wells

        metadata_columns = _metadata_columns_for_raw_curves(merged_df)
        selected_group_column = None
        if metadata_columns:
            selected_group_column = st.selectbox(
                "Metadata column for hover labels (optional)",
                options=["None", *metadata_columns],
                index=0,
                key="analyze_raw_curve_group_column",
            )
            if selected_group_column == "None":
                selected_group_column = None

        raw_plot_df = _prepare_raw_curve_plot_df(
            filtered_tidy_df,
            wells_to_plot=wells_to_plot,
            merged_df=merged_df,
            group_column=selected_group_column,
        )

        fig = px.line(
            raw_plot_df,
            x="time",
            y="value",
            color="well",
            line_group="well",
            labels={"time": "Elapsed time (minutes)", "value": "Raw value", "well": "Well"},
            title=f"Raw {config.get('signal_name', 'OD') if config else 'OD'} curves",
            custom_data=["metadata_group"],
        )
        fig.update_traces(mode="lines", opacity=0.55, line={"width": 1.3})
        if selected_group_column is not None:
            fig.update_traces(
                hovertemplate=(
                    "Well: %{fullData.name}<br>"
                    "Time (min): %{x:.3f}<br>"
                    "Value: %{y:.5g}<br>"
                    f"{selected_group_column}: %{{customdata[0]}}<extra></extra>"
                )
            )
        else:
            fig.update_traces(
                hovertemplate="Well: %{fullData.name}<br>Time (min): %{x:.3f}<br>Value: %{y:.5g}<extra></extra>"
            )
        st.plotly_chart(fig, use_container_width=True, key="analyze_raw_curves_plot")

    st.subheader("8. Results / Export")
    if filtered_tidy_df is None:
        st.info("Results/export placeholders will activate after parsing.")
        return

    signal_slug = (config.get("signal_name", "OD") if config else "OD").strip().replace(" ", "_")
    st.caption("Download parsed tidy measurements, merged data, selected features, and QC tables.")
    st.download_button(
        label="Download tidy (CSV)",
        data=filtered_tidy_df.to_csv(index=False),
        file_name=f"rosettier_tidy_{signal_slug}.csv",
        mime="text/csv",
        key="download_tidy_csv",
        on_click="ignore",
    )
    if merged_df is not None:
        st.download_button(
            label="Download merged data (CSV)",
            data=merged_df.to_csv(index=False),
            file_name=f"rosettier_merged_{signal_slug}.csv",
            mime="text/csv",
            key="download_merged_csv",
            on_click="ignore",
        )

    if qc is not None:
        st.download_button(
            label="Download QC missing overall (CSV)",
            data=qc["missing"]["overall"].to_csv(index=False),
            file_name=f"rosettier_qc_missing_overall_{signal_slug}.csv",
            mime="text/csv",
            key="download_qc_missing_overall_csv",
            on_click="ignore",
        )
        st.download_button(
            label="Download QC missing per well (CSV)",
            data=qc["missing"]["per_well"].to_csv(index=False),
            file_name=f"rosettier_qc_missing_per_well_{signal_slug}.csv",
            mime="text/csv",
            key="download_qc_missing_per_well_csv",
            on_click="ignore",
        )
        st.download_button(
            label="Download QC constant wells (CSV)",
            data=qc["constant_wells"].to_csv(index=False),
            file_name=f"rosettier_qc_constant_wells_{signal_slug}.csv",
            mime="text/csv",
            key="download_qc_constant_wells_csv",
            on_click="ignore",
        )
        st.download_button(
            label="Download QC outlier wells (CSV)",
            data=qc["outlier_wells"].to_csv(index=False),
            file_name=f"rosettier_qc_outlier_wells_{signal_slug}.csv",
            mime="text/csv",
            key="download_qc_outlier_wells_csv",
            on_click="ignore",
        )
        st.download_button(
            label="Download QC edge effects (CSV)",
            data=qc["edge_effects"].to_csv(index=False),
            file_name=f"rosettier_qc_edge_effects_{signal_slug}.csv",
            mime="text/csv",
            key="download_qc_edge_effects_csv",
            on_click="ignore",
        )

    if features_df is not None and features_df.shape[1] > 3:
        st.download_button(
            label="Download features (CSV)",
            data=features_df.to_csv(index=False),
            file_name=f"rosettier_features_{signal_slug}.csv",
            mime="text/csv",
            key="download_features_csv",
            on_click="ignore",
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
    plate_size = st.sidebar.selectbox("Plate size", options=[96, 384], index=0, key="sidebar_plate_size")
    mode = st.sidebar.selectbox("Mode", options=["Create Rosetta", "Analyze Data"], index=0, key="sidebar_mode")

    if mode == "Create Rosetta":
        _render_create_rosetta(st, plate_size=plate_size)
    else:
        _render_analyze_data(st, plate_size=plate_size)


if __name__ == "__main__":
    main()

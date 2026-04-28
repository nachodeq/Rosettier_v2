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
    """Return whether event includes a non-empty selection payload."""
    if not event:
        return False
    selection = event.get("selection")
    if not selection:
        return False
    points = selection.get("points") or []
    return len(points) > 0


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


def _resolve_feature_column(features_df: pd.DataFrame, signal_name: str, feature_name: str) -> str | None:
    """Resolve selected feature to an existing feature column."""
    normalized_signal_name = str(signal_name).strip() or "OD"
    preferred = f"{normalized_signal_name}_{feature_name}"
    if preferred in features_df.columns:
        return preferred
    if feature_name in features_df.columns:
        return feature_name
    return None


def _candidate_replicate_columns(columns: list[str]) -> list[str]:
    """Return metadata columns that likely describe replicate identity."""
    replicate_tokens = ("replicate", "replica", "rtecnica", "technical_replicate", "rep")
    candidates: list[str] = []
    for column in columns:
        normalized = str(column).strip().lower()
        if any(token in normalized for token in replicate_tokens):
            candidates.append(column)
    return candidates


def _prepare_feature_comparison_table(
    *,
    features_df: pd.DataFrame,
    merged_df: pd.DataFrame | None,
    feature_column: str,
    group_columns: list[str],
    color_column: str | None = None,
    facet_column: str | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build well-level comparison table used for feature boxplots."""
    comparison_df = features_df[["well", feature_column]].copy()
    if merged_df is not None:
        reserved = {"time", "value"}
        metadata_columns = [column for column in merged_df.columns if column not in reserved]
        metadata_lookup = (
            merged_df[metadata_columns]
            .dropna(subset=["well"])
            .drop_duplicates(subset=["well"], keep="first")
            .copy()
        )
        comparison_df = comparison_df.merge(metadata_lookup, on="well", how="left")

    for required_col in [*group_columns, color_column, facet_column]:
        if required_col is not None and required_col not in comparison_df.columns:
            comparison_df[required_col] = pd.NA

    missing_group_counts = {
        group_column: int(comparison_df[group_column].isna().sum()) if group_column in comparison_df.columns else len(comparison_df)
        for group_column in group_columns
    }
    return comparison_df, missing_group_counts


def _build_group_label_column(comparison_df: pd.DataFrame, group_columns: list[str]) -> pd.Series:
    """Create a composite grouping label from one or more metadata columns."""
    labels = []
    for _, row in comparison_df.iterrows():
        parts = []
        for group_column in group_columns:
            value = row.get(group_column)
            value_label = "—" if pd.isna(value) else str(value)
            parts.append(f"{group_column}={value_label}")
        labels.append(" | ".join(parts))
    return pd.Series(labels, index=comparison_df.index)


def _comparison_plot_mode(comparison_df: pd.DataFrame) -> str:
    """Return plot mode: box for >=3 rows, points for <3 rows."""
    return "box" if len(comparison_df) >= 3 else "points"


def _combine_qc_outputs_for_export(qc: dict) -> pd.DataFrame:
    """Combine QC outputs into one tidy export table."""
    component_frames: list[pd.DataFrame] = []

    missing_bundle = qc.get("missing")
    if isinstance(missing_bundle, dict):
        for scope, scope_df in missing_bundle.items():
            if isinstance(scope_df, pd.DataFrame):
                frame = scope_df.copy()
                frame.insert(0, "qc_scope", scope)
                frame.insert(0, "qc_component", "missing_values")
                component_frames.append(frame)

    for component in ["constant_wells", "outlier_wells", "edge_effects"]:
        component_df = qc.get(component)
        if isinstance(component_df, pd.DataFrame):
            frame = component_df.copy()
            frame.insert(0, "qc_scope", "summary")
            frame.insert(0, "qc_component", component)
            component_frames.append(frame)

    if not component_frames:
        return pd.DataFrame(columns=["qc_component", "qc_scope"])
    return pd.concat(component_frames, ignore_index=True, sort=False)


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

    if merged_df is None or not group_column:
        plot_df["metadata_label"] = "All wells"
        return plot_df.sort_values(["well", "time"]).reset_index(drop=True)

    if group_column not in merged_df.columns:
        plot_df["metadata_label"] = "All wells"
        return plot_df.sort_values(["well", "time"]).reset_index(drop=True)

    group_lookup = (
        merged_df[["well", group_column]]
        .dropna(subset=["well"])
        .drop_duplicates(subset=["well"], keep="first")
        .rename(columns={group_column: "group_metadata_label"})
    )
    plot_df = plot_df.merge(group_lookup, on="well", how="left")
    plot_df["metadata_label"] = plot_df["group_metadata_label"].fillna("—").astype(str)
    plot_df = plot_df.drop(columns=["group_metadata_label"])
    return plot_df.sort_values(["well", "time"]).reset_index(drop=True)


def _resolve_raw_curve_group_column(
    merged_df: pd.DataFrame | None,
    selected_group_column: str | None,
) -> tuple[str | None, str | None]:
    """Resolve raw-curve metadata grouping safely, returning (column, warning)."""
    if not selected_group_column:
        return None, None
    if merged_df is None:
        return None, f"Selected metadata column '{selected_group_column}' is unavailable (no merged metadata)."
    if selected_group_column not in merged_df.columns:
        return None, f"Selected metadata column '{selected_group_column}' is unavailable in merged data."
    return selected_group_column, None


def _rename_value_column_for_signal(df: pd.DataFrame, signal_name: str) -> pd.DataFrame:
    """Return a copy with canonical `value` renamed for user-facing display."""
    if "value" not in df.columns:
        return df.copy()
    renamed = df.copy()
    label = str(signal_name).strip() or "OD"
    return renamed.rename(columns={"value": label})


def _metadata_color_value_map(plot_df: pd.DataFrame, metadata_column: str | None) -> dict[str, str]:
    """Return deterministic colors for metadata values used in raw curve grouping."""
    if not metadata_column or metadata_column not in plot_df.columns:
        return {}
    unique_values = sorted(plot_df[metadata_column].dropna().astype(str).unique().tolist())
    if not unique_values:
        return {}
    palette = [
        "#4c78a8",
        "#f58518",
        "#54a24b",
        "#e45756",
        "#72b7b2",
        "#b279a2",
        "#ff9da6",
        "#9d755d",
        "#bab0ac",
        "#2f4b7c",
    ]
    return {value: palette[idx % len(palette)] for idx, value in enumerate(unique_values)}


def _filter_selected_wells(tidy_df: pd.DataFrame, selected_wells: list[str]) -> pd.DataFrame:
    """Return wells filtered by plate selection; empty selection means all wells."""
    wells = sorted(tidy_df["well"].dropna().astype(str).unique().tolist())
    wells_to_plot = selected_wells if selected_wells else wells
    return tidy_df.loc[tidy_df["well"].isin(wells_to_plot)].copy()


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
    """Mode: parse one or more signals, show raw curves first, and keep QC secondary."""
    st.header("Analyze Data")

    if "analyze_results" not in st.session_state:
        st.session_state["analyze_results"] = {}

    session_rosetta_available = "rosetta_df" in st.session_state

    st.subheader("1. Rosetta source")
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
    signal_count = int(
        st.number_input(
            "Number of signals/files",
            min_value=1,
            max_value=8,
            value=int(st.session_state.get("analyze_signal_count", 1)),
            step=1,
            key="analyze_signal_count",
            help="Each uploaded plate-reader file corresponds to one named signal.",
        )
    )

    st.subheader("2. Inputs")
    signal_entries: list[dict[str, object]] = []
    for idx in range(signal_count):
        with st.expander(f"Signal {idx + 1}", expanded=(idx == 0)):
            uploaded_file = st.file_uploader(
                f"Measurement file for signal {idx + 1} (CSV/TSV; wide format)",
                type=["csv", "tsv"],
                key=f"analyze_measurements_upload_{idx}",
            )
            signal_name = st.text_input(
                "Signal name",
                value=f"Signal_{idx + 1}",
                help="Examples: OD, GFP, RFP, luminescence.",
                key=f"analyze_signal_name_{idx}",
            )
            delimiter_choice = st.selectbox(
                "Delimiter",
                options=["auto", "tab", "comma", "semicolon"],
                index=0,
                key=f"analyze_delimiter_{idx}",
            )
            decimal_choice = st.selectbox(
                "Decimal separator",
                options=["auto", "comma", "point"],
                index=0,
                key=f"analyze_decimal_{idx}",
            )
            time_column_name = st.text_input("Time column name", value="Time", key=f"analyze_time_column_{idx}")
            signal_entries.append(
                {
                    "index": idx,
                    "uploaded_file": uploaded_file,
                    "signal_name": signal_name,
                    "delimiter": delimiter_choice,
                    "decimal": decimal_choice,
                    "time_column": time_column_name,
                }
            )

    st.subheader("3. Analysis setup")
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
        valid_signals = [entry for entry in signal_entries if entry["uploaded_file"] is not None]
        legacy_uploaded_file = st.session_state.get("analyze_measurements_upload")
        if not valid_signals and legacy_uploaded_file is not None:
            valid_signals = [
                {
                    "index": 0,
                    "uploaded_file": legacy_uploaded_file,
                    "signal_name": st.session_state.get("analyze_signal_name_0", "Signal_1"),
                    "delimiter": st.session_state.get("analyze_delimiter_0", "auto"),
                    "decimal": st.session_state.get("analyze_decimal_0", "auto"),
                    "time_column": st.session_state.get("analyze_time_column_0", "Time"),
                }
            ]
        if not valid_signals:
            st.info("Upload at least one measurements file to run analysis.")
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

            layout_well_column = None
            if layout_df is not None:
                layout_well_column = "well" if "well" in layout_df.columns else "Well"

            config = {
                "enable_time_filter": enable_time_filter,
                "min_time": float(min_time),
                "max_time": float(max_time),
                "selected_features": selected_features,
                "threshold": threshold,
            }

            st.session_state["analyze_results"] = {"config": config}

            signal_payloads: list[dict[str, object]] = []
            for entry in valid_signals:
                uploaded_file = entry["uploaded_file"]
                signal_payloads.append(
                    {
                        "index": entry["index"],
                        "signal_name": (str(entry["signal_name"]).strip() or f"Signal_{entry['index'] + 1}"),
                        "delimiter": entry["delimiter"],
                        "decimal": entry["decimal"],
                        "time_column": entry["time_column"],
                        "measurement_text": uploaded_file.getvalue().decode("utf-8"),
                    }
                )
            st.session_state["analyze_results"]["signals"] = signal_payloads
            st.session_state["analyze_results"]["layout_df"] = layout_df
            st.session_state["analyze_results"]["layout_well_column"] = layout_well_column
            st.session_state["analyze_results"]["errors"] = []

    results = st.session_state["analyze_results"]

    config = results.get("config")

    st.subheader("4. Validate, parse, visualize, and export")
    if "signals" not in results:
        st.info("Configure analysis setup and click 'Run analysis'.")
        return

    signal_payloads = results.get("signals", [])
    if not signal_payloads:
        st.info("No signal payloads available to render.")
        return

    signal_labels = [str(payload["signal_name"]) for payload in signal_payloads]
    rendered_signal_results: list[dict[str, object]] = []
    signal_tabs = st.tabs(signal_labels)
    for signal_tab, payload in zip(signal_tabs, signal_payloads, strict=False):
        with signal_tab:
            tidy_df: pd.DataFrame | None = None
            filtered_tidy_df: pd.DataFrame | None = None
            merged_df: pd.DataFrame | None = None
            features_df: pd.DataFrame | None = None
            qc: dict | None = None
            signal_index = int(payload.get("index", 0))
            signal_name = str(payload["signal_name"]).strip() or "OD"
            signal_slug = signal_name.replace(" ", "_")
            signal_key_slug = f"{signal_index}_{signal_slug}"
            st.markdown(f"### Signal: `{signal_name}`")

            st.caption("Parsed preview")
            try:
                tidy_df = parse_plate_reader_wide(
                    payload["measurement_text"],
                    plate_size=plate_size,
                    time_col=str(payload["time_column"]),
                    delimiter=str(payload["delimiter"]),
                    decimal=str(payload["decimal"]),
                )
                filtered_tidy_df = _filter_tidy_by_time_window(
                    tidy_df,
                    enable_time_filter=bool(config.get("enable_time_filter")) if config else False,
                    min_time=config.get("min_time") if config else None,
                    max_time=config.get("max_time") if config else None,
                )
                tidy_display_df = _rename_value_column_for_signal(tidy_df, signal_name=signal_name)
                st.write(
                    f"Parsed summary: {len(tidy_df)} rows, {tidy_df['well'].nunique()} wells, "
                    f"{tidy_df['time'].nunique()} timepoints, time range {tidy_df['time'].min()} to {tidy_df['time'].max()} minutes."
                )
                st.dataframe(tidy_display_df, use_container_width=True)
                if filtered_tidy_df is not None and len(filtered_tidy_df) != len(tidy_df):
                    st.caption(
                        f"Preview only (time-filtered tidy): {len(filtered_tidy_df)} rows after time filtering."
                    )
                    filtered_preview_df = _rename_value_column_for_signal(
                        filtered_tidy_df.head(12),
                        signal_name=signal_name,
                    )
                    st.dataframe(filtered_preview_df, use_container_width=True)
            except Exception as exc:  # pragma: no cover - defensive streamlit display
                st.error(f"Failed to parse measurements for {signal_name}: {exc}")
                continue

            layout_df = results.get("layout_df")
            layout_well_column = results.get("layout_well_column")
            if filtered_tidy_df is not None and layout_df is not None:
                try:
                    validated_layout = load_layout(layout_df, plate_size=plate_size, well_col=layout_well_column)
                    merged_df = merge_measurements_with_layout(
                        filtered_tidy_df,
                        validated_layout,
                        plate_size=plate_size,
                        layout_well_col=layout_well_column,
                    )
                    st.caption("Merged preview")
                    st.write(
                        f"Merged summary: {len(merged_df)} rows, {merged_df['well'].nunique()} wells, "
                        f"{merged_df['time'].nunique()} timepoints, time range {merged_df['time'].min()} to {merged_df['time'].max()} minutes."
                    )
                    merged_preview_df = _rename_value_column_for_signal(merged_df, signal_name=signal_name)
                    st.dataframe(merged_preview_df, use_container_width=True)
                except Exception as exc:  # pragma: no cover - defensive streamlit display
                    st.error(f"Failed to validate/merge Rosetta layout for {signal_name}: {exc}")

            st.markdown("#### Raw curves")
            available_wells = sorted(filtered_tidy_df["well"].dropna().astype(str).unique().tolist())
            selected_wells_key = f"analyze_selected_wells_{signal_key_slug}"
            if selected_wells_key not in st.session_state:
                st.session_state[selected_wells_key] = []
            existing_selected_wells = [
                well for well in st.session_state[selected_wells_key] if well in set(available_wells)
            ]
            if existing_selected_wells != st.session_state[selected_wells_key]:
                st.session_state[selected_wells_key] = existing_selected_wells
            multiselect_key = f"analyze_well_selector_{signal_key_slug}"
            selected_wells = st.multiselect(
                "Wells to plot (optional; leave empty for all wells)",
                options=available_wells,
                default=existing_selected_wells,
                key=multiselect_key,
                help="Search and select wells. Empty selection plots all wells.",
            )
            st.session_state[selected_wells_key] = selected_wells
            if st.button("Clear plate selection", key=f"analyze_clear_plate_selection_{signal_key_slug}"):
                st.session_state[selected_wells_key] = []
                st.rerun()
            st.caption(
                "No wells selected plots all wells. "
                f"Current selection count: {len(st.session_state[selected_wells_key])}"
            )

            wells_filtered_df = _filter_selected_wells(filtered_tidy_df, st.session_state[selected_wells_key])
            metadata_columns = _metadata_columns_for_raw_curves(merged_df)
            selected_group_column = None
            if metadata_columns:
                selected_group_column = st.selectbox(
                    "Metadata column for color/hover grouping (optional)",
                    options=["None", *metadata_columns],
                    index=0,
                    key=f"analyze_raw_curve_group_column_{signal_key_slug}",
                )
                if selected_group_column == "None":
                    selected_group_column = None
            resolved_group_column, group_column_warning = _resolve_raw_curve_group_column(merged_df, selected_group_column)
            if group_column_warning:
                st.warning(group_column_warning)
            plot_df = _prepare_raw_curve_plot_df(
                wells_filtered_df,
                wells_to_plot=sorted(wells_filtered_df["well"].dropna().astype(str).unique().tolist()),
                merged_df=merged_df,
                group_column=resolved_group_column,
            )

            import plotly.express as px

            color_map = _metadata_color_value_map(plot_df, "metadata_label" if resolved_group_column else None)
            if resolved_group_column:
                color_column = "metadata_label"
                labels = {
                    "time": "Elapsed time (minutes)",
                    "value": signal_name,
                    "metadata_label": resolved_group_column,
                }
            else:
                color_column = "well_color"
                plot_df[color_column] = "All wells"
                labels = {"time": "Elapsed time (minutes)", "value": signal_name}
            fig = px.line(
                plot_df,
                x="time",
                y="value",
                line_group="well",
                color=color_column,
                color_discrete_map=color_map if resolved_group_column else {"All wells": "#4c78a8"},
                labels=labels,
                title=f"Raw {signal_name} curves",
                custom_data=["well", "metadata_label"],
            )
            hover_tail = (
                f"<br>{resolved_group_column}: %{{customdata[1]}}<extra></extra>"
                if resolved_group_column
                else "<extra></extra>"
            )
            fig.update_traces(
                mode="lines",
                opacity=0.55,
                line={"width": 1.3},
                hovertemplate=f"Well: %{{customdata[0]}}<br>Time (min): %{{x:.3f}}<br>{signal_name}: %{{y:.5g}}{hover_tail}",
            )
            st.plotly_chart(fig, use_container_width=True, key=f"analyze_raw_curves_plot_{signal_key_slug}")

            try:
                feature_source = merged_df if merged_df is not None else filtered_tidy_df
                features_df = _compute_selected_features(
                    feature_source,
                    selected_features=config.get("selected_features", []) if config else [],
                    threshold=config.get("threshold") if config else None,
                    signal_name=signal_name,
                )
            except Exception as exc:  # pragma: no cover - defensive streamlit display
                st.error(f"Failed to extract features for {signal_name}: {exc}")
                features_df = None

            with st.expander("QC summary (compact)", expanded=False):
                try:
                    qc = qc_summary(filtered_tidy_df)
                    missing_overall = qc["missing"]["overall"]
                    missing_count = int(missing_overall["n_missing"].sum()) if "n_missing" in missing_overall.columns else 0
                    constant_count = int(len(qc["constant_wells"]))
                    outlier_count = int(len(qc["outlier_wells"]))
                    st.write(
                        f"Missing values: **{missing_count}** | "
                        f"Constant wells: **{constant_count}** | "
                        f"Outlier wells: **{outlier_count}**"
                    )
                    with st.expander("Optional QC details", expanded=False):
                        st.dataframe(missing_overall, use_container_width=True)
                        st.dataframe(qc["constant_wells"].head(12), use_container_width=True)
                        st.dataframe(qc["outlier_wells"].head(12), use_container_width=True)
                        st.dataframe(qc["edge_effects"], use_container_width=True)
                except Exception as exc:  # pragma: no cover - defensive streamlit display
                    st.error(f"Failed to compute QC summary for {signal_name}: {exc}")

            st.markdown("#### Results and export")
            st.caption("Preview only (filtered tidy)")
            filtered_display_df = _rename_value_column_for_signal(filtered_tidy_df.head(12), signal_name=signal_name)
            st.dataframe(filtered_display_df, use_container_width=True)
            if features_df is not None and features_df.shape[1] > 3:
                st.caption("Preview only (features)")
                st.dataframe(features_df.head(12), use_container_width=True)
            tidy_export_df = _rename_value_column_for_signal(filtered_tidy_df, signal_name=signal_name)
            st.download_button(
                label="Download tidy (CSV)",
                data=tidy_export_df.to_csv(index=False),
                file_name=f"rosettier_tidy_{signal_slug}.csv",
                mime="text/csv",
                key=f"download_tidy_csv_{signal_key_slug}",
                on_click="ignore",
            )
            if merged_df is not None:
                merged_export_df = _rename_value_column_for_signal(merged_df, signal_name=signal_name)
                st.download_button(
                    label="Download merged data (CSV)",
                    data=merged_export_df.to_csv(index=False),
                    file_name=f"rosettier_merged_{signal_slug}.csv",
                    mime="text/csv",
                    key=f"download_merged_csv_{signal_key_slug}",
                    on_click="ignore",
                )
            if features_df is not None and features_df.shape[1] > 3:
                st.download_button(
                    label="Download features (CSV)",
                    data=features_df.to_csv(index=False),
                    file_name=f"rosettier_features_{signal_slug}.csv",
                    mime="text/csv",
                    key=f"download_features_csv_{signal_key_slug}",
                    on_click="ignore",
                )
            if qc is not None:
                qc_export_df = _combine_qc_outputs_for_export(qc)
                st.download_button(
                    label="Download QC summary",
                    data=qc_export_df.to_csv(index=False),
                    file_name=f"rosettier_qc_summary_{signal_slug}.csv",
                    mime="text/csv",
                    key=f"download_qc_summary_csv_{signal_key_slug}",
                    on_click="ignore",
                )

            rendered_signal_results.append(
                {
                    "signal_name": signal_name,
                    "signal_slug": signal_slug,
                    "features_df": features_df,
                    "merged_df": merged_df,
                }
            )

    st.markdown("### Compare features")
    available_comparison = [
        signal_result
        for signal_result in rendered_signal_results
        if isinstance(signal_result.get("features_df"), pd.DataFrame)
        and signal_result["features_df"] is not None
        and signal_result["features_df"].shape[1] > 3
    ]
    if not available_comparison:
        st.info("No extracted feature tables are available yet for comparison plotting.")
        return

    comparison_signal_names = [str(signal_result["signal_name"]) for signal_result in available_comparison]
    selected_signal_name = st.selectbox(
        "Signal",
        options=comparison_signal_names,
        index=0,
        key="compare_features_signal",
    )
    selected_signal = next(
        signal_result for signal_result in available_comparison if str(signal_result["signal_name"]) == selected_signal_name
    )
    selected_signal_slug = str(selected_signal["signal_slug"])
    selected_features_df = selected_signal["features_df"]
    selected_merged_df = selected_signal["merged_df"]

    selectable_features: list[tuple[str, str]] = []
    for feature_name in ["auc", "endpoint", "max_slope", "time_to_threshold"]:
        feature_column = _resolve_feature_column(selected_features_df, selected_signal_name, feature_name)
        if feature_column is not None:
            selectable_features.append((feature_name, feature_column))
    if not selectable_features:
        st.info("No selectable feature columns were found for this signal.")
        return

    feature_lookup = {feature_name: feature_column for feature_name, feature_column in selectable_features}
    selected_feature_name = st.selectbox(
        "Feature",
        options=[feature_name for feature_name, _ in selectable_features],
        format_func=lambda feature: _FEATURE_LABELS.get(feature, feature),
        key="compare_features_feature_name",
    )
    selected_feature_column = feature_lookup[selected_feature_name]

    metadata_columns = _metadata_columns_for_raw_curves(selected_merged_df)
    if not metadata_columns:
        st.info("Comparison plotting requires merged Rosetta metadata columns.")
        return

    selected_group_columns = st.multiselect(
        "Grouping columns",
        options=metadata_columns,
        default=[metadata_columns[0]],
        key="compare_features_group_columns",
        help="Select one or more metadata columns to define groups.",
    )
    if not selected_group_columns:
        st.info("Select at least one grouping column.")
        return
    selected_color_column = st.selectbox(
        "Color column (optional)",
        options=["None", *metadata_columns],
        index=0,
        key="compare_features_color_column",
    )
    if selected_color_column == "None":
        selected_color_column = None
    selected_facet_column = st.selectbox(
        "Facet column (optional)",
        options=["None", *metadata_columns],
        index=0,
        key="compare_features_facet_column",
    )
    if selected_facet_column == "None":
        selected_facet_column = None

    comparison_df, missing_group_counts = _prepare_feature_comparison_table(
        features_df=selected_features_df,
        merged_df=selected_merged_df,
        feature_column=selected_feature_column,
        group_columns=selected_group_columns,
        color_column=selected_color_column,
        facet_column=selected_facet_column,
    )
    for group_column, missing_group_count in missing_group_counts.items():
        if missing_group_count > 0:
            st.warning(f"Grouping column '{group_column}' has {missing_group_count} well(s) with missing labels.")
    comparison_df = comparison_df.copy()
    group_label_column = "__compare_group_label__"
    comparison_df[group_label_column] = _build_group_label_column(comparison_df, selected_group_columns)
    category_count = comparison_df[group_label_column].dropna().astype(str).nunique()
    if category_count > 20:
        st.warning(
            f"Selected grouping has {category_count} categories; the plot may be crowded."
        )

    replicate_columns = _candidate_replicate_columns(metadata_columns)
    hover_columns = [*selected_group_columns]
    for optional_column in [selected_color_column, selected_facet_column, *replicate_columns]:
        if optional_column and optional_column in comparison_df.columns and optional_column not in hover_columns:
            hover_columns.append(optional_column)

    import plotly.express as px

    hover_data = {selected_feature_column: ":.5g"}
    hover_data.update({column: True for column in hover_columns})
    plot_mode = _comparison_plot_mode(comparison_df)
    if plot_mode == "box":
        fig = px.box(
            comparison_df,
            x=group_label_column,
            y=selected_feature_column,
            color=selected_color_column,
            facet_col=selected_facet_column,
            points="all",
            hover_name="well",
            hover_data=hover_data,
            labels={
                group_label_column: " | ".join(selected_group_columns),
                selected_feature_column: _FEATURE_LABELS.get(selected_feature_name, selected_feature_name),
            },
            title=(
                f"{selected_signal_name}: {_FEATURE_LABELS.get(selected_feature_name, selected_feature_name)} "
                f"by {' + '.join(selected_group_columns)}"
            ),
        )
        fig.update_traces(jitter=0.35, pointpos=0.0, marker={"size": 7, "opacity": 0.75})
        fig.update_layout(boxmode="group")
    else:
        fig = px.strip(
            comparison_df,
            x=group_label_column,
            y=selected_feature_column,
            color=selected_color_column,
            facet_col=selected_facet_column,
            hover_name="well",
            hover_data=hover_data,
            labels={
                group_label_column: " | ".join(selected_group_columns),
                selected_feature_column: _FEATURE_LABELS.get(selected_feature_name, selected_feature_name),
            },
            title=(
                f"{selected_signal_name}: {_FEATURE_LABELS.get(selected_feature_name, selected_feature_name)} "
                f"points by {' + '.join(selected_group_columns)} (<3 wells)"
            ),
        )
        fig.update_traces(jitter=0.35, marker={"size": 8, "opacity": 0.8})
    st.plotly_chart(fig, use_container_width=True, key=f"compare_features_plot_{selected_signal_slug}")

    image_col1, image_col2 = st.columns(2)
    with image_col1:
        try:
            png_bytes = fig.to_image(format="png")
            st.download_button(
                label="Download plot (PNG)",
                data=png_bytes,
                file_name=(
                    f"rosettier_compare_plot_{selected_signal_slug}_{selected_feature_name}_"
                    f"by_{'_'.join(selected_group_columns)}.png"
                ),
                mime="image/png",
                key=f"download_compare_plot_png_{selected_signal_slug}",
                on_click="ignore",
            )
        except Exception as exc:  # pragma: no cover - depends on runtime image backend
            st.warning(f"PNG export unavailable in this environment: {exc}")
    with image_col2:
        try:
            svg_bytes = fig.to_image(format="svg")
            st.download_button(
                label="Download plot (SVG)",
                data=svg_bytes,
                file_name=(
                    f"rosettier_compare_plot_{selected_signal_slug}_{selected_feature_name}_"
                    f"by_{'_'.join(selected_group_columns)}.svg"
                ),
                mime="image/svg+xml",
                key=f"download_compare_plot_svg_{selected_signal_slug}",
                on_click="ignore",
            )
        except Exception as exc:  # pragma: no cover - depends on runtime image backend
            st.warning(f"SVG export unavailable in this environment: {exc}")

    st.caption("Comparison table used for plotting")
    st.dataframe(comparison_df, use_container_width=True)
    st.download_button(
        label="Download comparison table (CSV)",
        data=comparison_df.to_csv(index=False),
        file_name=(
            f"rosettier_compare_{selected_signal_slug}_{selected_feature_name}_by_{'_'.join(selected_group_columns)}.csv"
        ),
        mime="text/csv",
        key=f"download_compare_table_{selected_signal_slug}_{selected_feature_name}_{'_'.join(selected_group_columns)}",
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

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


def _rosetta_template(spec: PlateSpec) -> pd.DataFrame:
    """Build default Rosetta metadata rows (one per canonical well)."""
    wells = spec.canonical_wells()
    return pd.DataFrame(
        {
            "well": wells,
            "strain": [""] * len(wells),
            "drug": [""] * len(wells),
            "concentration": [""] * len(wells),
            "replicate": [""] * len(wells),
            "control_type": [""] * len(wells),
            "group": [""] * len(wells),
        }
    )


def _render_create_rosetta(st, plate_size: int) -> None:
    """Workflow: create and export Rosetta metadata."""
    spec = PlateSpec.from_size(plate_size)
    wells = spec.canonical_wells()

    st.header("Create Rosetta")

    st.subheader("1. Plate preview")
    preview = pd.DataFrame({"well": wells})
    st.dataframe(preview, use_container_width=True, height=240)

    st.subheader("2. Metadata editor placeholder")
    st.caption(
        "Define variables such as `strain`, `drug`, `concentration`, `replicate`, `control_type`, and `group`."
    )
    rosetta_df = _rosetta_template(spec)
    st.dataframe(rosetta_df.head(12), use_container_width=True)
    st.caption(f"Template has {len(rosetta_df)} rows (one per well).")

    st.subheader("3. Validate Rosetta")
    try:
        validate_complete_well_set(rosetta_df["well"].tolist(), plate_size=plate_size)
        st.success("Rosetta validation passed: well set matches selected plate size.")
    except Exception as exc:  # pragma: no cover - defensive streamlit display
        st.error(f"Rosetta validation failed: {exc}")

    st.subheader("4. Export Rosetta")
    export_format = st.selectbox("Export format", options=["csv", "tsv"], key="rosetta_export_format")
    delimiter = "," if export_format == "csv" else "\t"
    mime = "text/csv" if export_format == "csv" else "text/tab-separated-values"
    file_name = f"rosetta_layout_{plate_size}.{export_format}"
    st.download_button(
        label=f"Download Rosetta ({export_format.upper()})",
        data=rosetta_df.to_csv(index=False, sep=delimiter),
        file_name=file_name,
        mime=mime,
    )


def _render_analyze_data(st, plate_size: int) -> None:
    """Workflow: validate, parse, QC and feature placeholders."""
    st.header("Analyze Data")

    st.subheader("1. Upload measurements")
    measurement_file = st.file_uploader(
        "Measurements file (CSV/TSV; wide format: rows=timepoints, columns=wells)",
        type=["csv", "tsv"],
        key="measurements_upload",
    )

    st.subheader("2. Upload Rosetta/layout")
    layout_file = st.file_uploader(
        "Rosetta/layout file (CSV/TSV; keyed by `well`)",
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

    if tidy_df is not None and layout_file is not None:
        layout_df = _read_uploaded_table(layout_file)
        try:
            validated_layout = load_layout(layout_df, plate_size=plate_size, well_col="well")
            tidy_df = merge_measurements_with_layout(tidy_df, validated_layout, plate_size=plate_size)
            st.success("Layout validated and merged.")
        except Exception as exc:  # pragma: no cover - defensive streamlit display
            st.error(f"Failed to validate/merge layout: {exc}")

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
    st.caption("App shell with two workflows. Core scientific logic remains in `rosettier` modules.")

    st.sidebar.header("Settings")
    plate_size = st.sidebar.selectbox("Plate size", options=[96, 384], index=0)
    workflow = st.sidebar.selectbox("Workflow", options=["Create Rosetta", "Analyze Data"], index=0)

    if workflow == "Create Rosetta":
        _render_create_rosetta(st, plate_size=plate_size)
    else:
        _render_analyze_data(st, plate_size=plate_size)


if __name__ == "__main__":
    main()

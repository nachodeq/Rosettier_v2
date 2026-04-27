"""Streamlit shell for Rosettier v2 local app."""

from __future__ import annotations


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
    st.caption("Local app shell — scientific logic remains in `rosettier` core modules.")

    sections = [
        "Upload measurements",
        "Upload layout",
        "Validate and parse",
        "QC summary",
        "Feature extraction",
        "Export",
    ]

    for section in sections:
        st.header(section)
        st.info("Placeholder: UI wiring will be added in a later iteration.")


if __name__ == "__main__":
    main()

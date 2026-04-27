from rosettier_app import app


class _StubStreamlit:
    def __init__(self):
        self.session_state = {}


def test_app_module_imports():
    assert app is not None


def test_main_exists():
    assert callable(app.main)


def test_map_96_well_to_384_well_legacy_offsets():
    mapped_well, mapped_row, mapped_column = app._map_96_well_to_384_well("A01", row_offset=0, col_offset=0)
    assert (mapped_well, mapped_row, mapped_column) == ("A01", "A", 1)

    mapped_well, mapped_row, mapped_column = app._map_96_well_to_384_well("A01", row_offset=0, col_offset=1)
    assert (mapped_well, mapped_row, mapped_column) == ("A02", "A", 2)

    mapped_well, mapped_row, mapped_column = app._map_96_well_to_384_well("A01", row_offset=1, col_offset=0)
    assert (mapped_well, mapped_row, mapped_column) == ("B01", "B", 1)

    mapped_well, mapped_row, mapped_column = app._map_96_well_to_384_well("A01", row_offset=1, col_offset=1)
    assert (mapped_well, mapped_row, mapped_column) == ("B02", "B", 2)


def test_combine_four_96_rosettas_creates_complete_384():
    plate_1 = app._build_rosetta_table(app.PlateSpec.from_size(96))
    plate_1["strain"] = "p1"
    plate_2 = app._build_rosetta_table(app.PlateSpec.from_size(96))
    plate_2["strain"] = "p2"
    plate_3 = app._build_rosetta_table(app.PlateSpec.from_size(96))
    plate_3["strain"] = "p3"
    plate_4 = app._build_rosetta_table(app.PlateSpec.from_size(96))
    plate_4["strain"] = "p4"

    combined = app._combine_four_96_rosettas([plate_1, plate_2, plate_3, plate_4])

    assert len(combined) == 384
    assert set(["well", "row", "column", "strain"]).issubset(set(combined.columns))

    a1 = combined.loc[combined["well"] == "A01"].iloc[0]
    a2 = combined.loc[combined["well"] == "A02"].iloc[0]
    b1 = combined.loc[combined["well"] == "B01"].iloc[0]
    b2 = combined.loc[combined["well"] == "B02"].iloc[0]

    assert a1["strain"] == "p1"
    assert a2["strain"] == "p2"
    assert b1["strain"] == "p3"
    assert b2["strain"] == "p4"


def test_copy_rosetta_editor_plate_state_copies_all_metadata_and_values():
    st = _StubStreamlit()

    source_df = app._build_rosetta_table(app.PlateSpec.from_size(96))
    source_df["strain"] = ""
    source_df["dose"] = ""
    source_df.loc[source_df["well"] == "A01", "strain"] = "WT"
    source_df.loc[source_df["well"] == "B03", "dose"] = "10uM"

    destination_df = app._build_rosetta_table(app.PlateSpec.from_size(96))
    destination_df["old_var"] = "old"

    st.session_state["combine_plate_1_df"] = source_df
    st.session_state["combine_plate_1_variables"] = ["strain", "dose"]
    st.session_state["combine_plate_1_selected_wells"] = ["A01", "B03"]

    st.session_state["combine_plate_2_df"] = destination_df
    st.session_state["combine_plate_2_variables"] = ["old_var"]
    st.session_state["combine_plate_2_selected_wells"] = []
    st.session_state["combine_plate_2_viz"] = "old_var"
    st.session_state["combine_plate_2_assign_variable"] = "old_var"

    app._copy_rosetta_editor_plate_state(
        st,
        source_prefix="combine_plate_1",
        destination_prefix="combine_plate_2",
        destination_widget_prefix="combine_plate_2",
    )

    copied_df = st.session_state["combine_plate_2_df"]
    assert set(["well", "row", "column", "strain", "dose"]).issubset(set(copied_df.columns))
    assert copied_df.loc[copied_df["well"] == "A01", "strain"].iloc[0] == "WT"
    assert copied_df.loc[copied_df["well"] == "B03", "dose"].iloc[0] == "10uM"
    assert st.session_state["combine_plate_2_variables"] == ["strain", "dose"]
    assert st.session_state["combine_plate_2_selected_wells"] == ["A01", "B03"]
    assert "combine_plate_2_viz" not in st.session_state
    assert "combine_plate_2_assign_variable" not in st.session_state


def test_copy_rosetta_editor_plate_state_does_not_mutate_source_plate():
    st = _StubStreamlit()
    source_df = app._build_rosetta_table(app.PlateSpec.from_size(96))
    source_df["strain"] = "source"
    st.session_state["combine_plate_1_df"] = source_df
    st.session_state["combine_plate_1_variables"] = ["strain"]
    st.session_state["combine_plate_1_selected_wells"] = ["A01"]

    st.session_state["combine_plate_3_df"] = app._build_rosetta_table(app.PlateSpec.from_size(96))
    st.session_state["combine_plate_3_variables"] = []
    st.session_state["combine_plate_3_selected_wells"] = []

    app._copy_rosetta_editor_plate_state(
        st,
        source_prefix="combine_plate_1",
        destination_prefix="combine_plate_3",
        destination_widget_prefix="combine_plate_3",
    )

    st.session_state["combine_plate_3_df"].loc[st.session_state["combine_plate_3_df"]["well"] == "A01", "strain"] = "destination-only"
    assert st.session_state["combine_plate_1_df"].loc[st.session_state["combine_plate_1_df"]["well"] == "A01", "strain"].iloc[0] == "source"

from rosettier_app import app


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

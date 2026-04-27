import pytest

from rosettier.exceptions import DuplicatedWellError, InvalidWellError, MissingWellError, PlateSizeMismatchError
from rosettier.plates import PlateSpec, infer_plate_size, normalize_well, validate_complete_well_set


def test_plate_spec_canonical_counts_for_96_and_384():
    assert len(PlateSpec.from_size(96).canonical_wells()) == 96
    assert len(PlateSpec.from_size(384).canonical_wells()) == 384


def test_normalize_well_is_case_insensitive_and_zero_padded():
    spec = PlateSpec.from_size(96)
    assert normalize_well("a1", spec) == "A01"


def test_invalid_well_raises():
    spec = PlateSpec.from_size(96)
    with pytest.raises(InvalidWellError):
        normalize_well("Z99", spec)


def test_duplicate_wells_after_normalization_raise():
    spec = PlateSpec.from_size(96)
    wells = spec.canonical_wells()
    wells[0] = "a1"
    wells[1] = "A01"
    with pytest.raises(DuplicatedWellError):
        validate_complete_well_set(wells, plate_size=96)


def test_missing_wells_raise_for_partial_plate():
    wells = PlateSpec.from_size(96).canonical_wells()[:-1]
    with pytest.raises(MissingWellError):
        validate_complete_well_set(wells, plate_size=96)


def test_infer_plate_size_from_complete_set_96_and_384():
    assert infer_plate_size(PlateSpec.from_size(96).canonical_wells()).size == 96
    assert infer_plate_size(PlateSpec.from_size(384).canonical_wells()).size == 384


def test_infer_plate_size_rejects_non_complete_set():
    with pytest.raises(PlateSizeMismatchError):
        infer_plate_size(["A01", "A02"])

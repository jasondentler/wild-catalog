from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.h3_index import gps_coordinates_to_h3_cell


def test_gps_coordinates_to_h3_cell_returns_cell_string() -> None:
    cell = gps_coordinates_to_h3_cell(
        GpsCoordinates(latitude=29.7604, longitude=-95.3698),
        resolution=5,
    )

    assert isinstance(cell, str)
    assert cell

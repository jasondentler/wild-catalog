from wild_catalog.core.types import BoundingBox, GpsCoordinates


def test_bounding_box_width_and_height() -> None:
    box = BoundingBox(xmin=10, ymin=20, xmax=30, ymax=55)

    assert box.width == 20
    assert box.height == 35


def test_gps_coordinates_stores_latitude_and_longitude() -> None:
    coordinates = GpsCoordinates(latitude=29.7604, longitude=-95.3698)

    assert coordinates.latitude == 29.7604
    assert coordinates.longitude == -95.3698

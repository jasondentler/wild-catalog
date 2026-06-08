import h3

from wild_catalog.core.types import GpsCoordinates


def gps_coordinates_to_h3_cell(
    gps_coordinates: GpsCoordinates,
    *,
    resolution: int,
) -> str:
    return h3.latlng_to_cell(
        gps_coordinates.latitude,
        gps_coordinates.longitude,
        resolution,
    )

from pydantic import BaseModel

from wild_catalog.api.gps_coordinates_response import GpsCoordinatesResponse
from wild_catalog.api.identified_object_response import IdentifiedObjectResponse


class IdentifyResponse(BaseModel):
    gps_coordinates: GpsCoordinatesResponse | None = None
    results: list[IdentifiedObjectResponse]

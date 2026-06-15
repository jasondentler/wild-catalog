from pydantic import BaseModel


class GpsCoordinatesResponse(BaseModel):
    latitude: float
    longitude: float

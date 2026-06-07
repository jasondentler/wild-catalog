from pydantic import BaseModel


class BoundingBoxResponse(BaseModel):
    xmin: int
    ymin: int
    xmax: int
    ymax: int
    width: int
    height: int


class PredictionResponse(BaseModel):
    confidence: float
    is_present: bool
    taxonomy: list[str]
    taxonomy_common_names: list[str]


class IdentifiedObjectResponse(BaseModel):
    bounding_box: BoundingBoxResponse
    bounding_box_with_margin: BoundingBoxResponse
    gps_coordinates: tuple[float, float] | None
    predictions: list[PredictionResponse]

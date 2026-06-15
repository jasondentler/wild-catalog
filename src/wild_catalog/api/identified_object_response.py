from pydantic import BaseModel

from wild_catalog.api.bounding_box_response import BoundingBoxResponse
from wild_catalog.api.prediction_response import PredictionResponse


class IdentifiedObjectResponse(BaseModel):
    bounding_box: BoundingBoxResponse
    bounding_box_with_margin: BoundingBoxResponse
    predictions: list[PredictionResponse]

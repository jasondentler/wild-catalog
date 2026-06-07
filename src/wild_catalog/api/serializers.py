from wild_catalog.api.response_models import (
    BoundingBoxResponse,
    IdentifiedObjectResponse,
    PredictionResponse,
)
from wild_catalog.core.types import BoundingBox
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyResult
from wild_catalog.taxonomy.types import EnrichedPrediction


def bounding_box_to_response(box: BoundingBox) -> BoundingBoxResponse:
    return BoundingBoxResponse(
        xmin=box.xmin,
        ymin=box.ymin,
        xmax=box.xmax,
        ymax=box.ymax,
        width=box.width,
        height=box.height,
    )


def prediction_to_response(prediction: EnrichedPrediction) -> PredictionResponse:
    return PredictionResponse(
        confidence=prediction.confidence,
        is_present=prediction.is_present,
        taxonomy=list(prediction.taxonomy),
        taxonomy_common_names=list(prediction.taxonomy_common_names),
    )


def identified_object_to_response(
    identified_object: IdentifiedObject,
) -> IdentifiedObjectResponse:
    gps_coordinates = identified_object.gps_coordinates

    return IdentifiedObjectResponse(
        bounding_box=bounding_box_to_response(identified_object.bounding_box),
        bounding_box_with_margin=bounding_box_to_response(
            identified_object.bounding_box_with_margin
        ),
        gps_coordinates=(
            (gps_coordinates.latitude, gps_coordinates.longitude)
            if gps_coordinates is not None
            else None
        ),
        predictions=[
            prediction_to_response(prediction)
            for prediction in identified_object.predictions
        ],
    )


def identify_result_to_response(
    result: IdentifyResult,
) -> list[IdentifiedObjectResponse]:
    return [
        identified_object_to_response(identified_object)
        for identified_object in result.objects
    ]


def identify_result_to_json(result: IdentifyResult) -> list[dict]:
    return [
        response.model_dump(mode="json")
        for response in identify_result_to_response(result)
    ]

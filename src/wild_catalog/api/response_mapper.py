from __future__ import annotations

import io
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import Response
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image

from wild_catalog.api.content_negotiation import ResponseFormat, ResponseSelection
from wild_catalog.api.response_models import (
    BoundingBoxResponse,
    GpsCoordinatesResponse,
    IdentifiedObjectResponse,
    IdentifyResponse,
    PredictionResponse,
)
from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.identify_pipeline.identify_result import (
    IdentifiedObject,
    IdentifyResult,
    Prediction,
)


def map_response(
    result: IdentifyResult | None,
    response_selection: ResponseSelection,
    payload: dict[str, object] | None = None,
) -> Response:
    if result is None:
        return Response(status_code=204)

    if payload is None:
        payload = map_identify_result_payload(result)

    if response_selection.response_format == ResponseFormat.JSON:
        response = JSONResponse(
            status_code=200,
            content=payload,
        )
        return response

    return map_multipart_response(result, response_selection, payload=payload)


def map_multipart_response(
    result: IdentifyResult,
    response_selection: ResponseSelection,
    payload: dict[str, object] | None = None,
) -> StreamingResponse:
    boundary = f"wildcatalog-{uuid.uuid4().hex}"
    if payload is None:
        payload = map_identify_result_payload(result)

    async def stream() -> AsyncIterator[bytes]:
        yield _multipart_json_part(boundary, payload)

        if response_selection.include_images:
            for index, obj in enumerate(result.objects):
                if obj.cropped_image is None:
                    continue
                yield _multipart_image_part(boundary, obj.cropped_image, index)

        yield f"--{boundary}--\r\n".encode()

    response = StreamingResponse(
        stream(),
        media_type=f'multipart/mixed; boundary="{boundary}"',
    )
    return response


def map_identify_result_payload(result: IdentifyResult) -> dict[str, object]:
    return _map_identify_result(result).model_dump()


def _map_identify_result(result: IdentifyResult) -> IdentifyResponse:
    return IdentifyResponse(
        gps_coordinates=_map_gps_coordinates(result.gps_coordinates),
        results=[_map_identified_object(obj) for obj in result.objects],
    )


def _map_identified_object(obj: IdentifiedObject) -> IdentifiedObjectResponse:
    return IdentifiedObjectResponse(
        bounding_box=_map_bounding_box(obj.bounding_box),
        bounding_box_with_margin=_map_bounding_box(obj.bounding_box_with_margin),
        predictions=[_map_prediction(prediction) for prediction in obj.predictions],
    )


def _map_bounding_box(box: BoundingBox) -> BoundingBoxResponse:
    return BoundingBoxResponse(
        xmin=box.xmin,
        ymin=box.ymin,
        xmax=box.xmax,
        ymax=box.ymax,
        width=box.width,
        height=box.height,
    )


def _map_gps_coordinates(
    gps_coordinates: GpsCoordinates | None,
) -> GpsCoordinatesResponse | None:
    if gps_coordinates is None:
        return None

    return GpsCoordinatesResponse(
        latitude=gps_coordinates.latitude,
        longitude=gps_coordinates.longitude,
    )


def _map_prediction(prediction: Prediction) -> PredictionResponse:
    return PredictionResponse(
        confidence=prediction.confidence,
        is_present=prediction.is_present,
        taxonomy=list(prediction.taxonomy),
        taxonomy_rank_names=list(prediction.taxonomy_rank_names),
        taxonomy_common_names=list(prediction.taxonomy_common_names),
    )


def _multipart_json_part(boundary: str, payload: dict[str, object]) -> bytes:
    body = json.dumps(payload).encode()
    return (
        f"--{boundary}\r\n"
        "Content-Type: application/json\r\n\r\n"
    ).encode() + body + b"\r\n"


def _multipart_image_part(boundary: str, image: Image.Image, index: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    body = buffer.getvalue()
    return (
        f"--{boundary}\r\n"
        "Content-Type: image/jpeg\r\n"
        f'Content-Disposition: inline; filename="object-{index + 1}.jpg"\r\n\r\n'
    ).encode() + body + b"\r\n"

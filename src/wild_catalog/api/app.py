import logging
from typing import Annotated, BinaryIO

from fastapi import Depends, FastAPI, Request
from fastapi.responses import Response

from wild_catalog.api.content_negotiation import select_identify_response_format
from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.api.errors import register_exception_handlers
from wild_catalog.api.logging import log_identify_request
from wild_catalog.api.multipart_request_mapper import create_multipart_form_command
from wild_catalog.api.openapi_schemas import IDENTIFY_REQUEST_OPENAPI_EXTRA
from wild_catalog.api.response_mapper import map_response
from wild_catalog.api.simple_request_mapper import create_request_body_command
from wild_catalog.pipeline.identify_command import IdentifyCommand
from wild_catalog.pipeline.identify_pipeline import IdentifyPipeline

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Wild Catalog")
register_exception_handlers(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/identify",
    dependencies=[Depends(log_identify_request)],
    openapi_extra=IDENTIFY_REQUEST_OPENAPI_EXTRA,
)
async def identify(
    request: Request,
    pipeline: Annotated[IdentifyPipeline, Depends(get_identify_pipeline)],
) -> Response:
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept")
    command: IdentifyCommand
    file: BinaryIO

    if content_type.startswith("multipart/form-data"):
        command, file = await create_multipart_form_command(request)
    else:
        command, file = await create_request_body_command(request)

    result = pipeline.execute(command, file)
    response_selection = select_identify_response_format(
        accept_header=accept_header,
        return_detected_images=result.return_detected_images,
    )

    response = map_response(
        result,
        response_selection,
    )

    return response

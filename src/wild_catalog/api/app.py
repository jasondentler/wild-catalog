import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, BinaryIO

from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import Response

from wild_catalog.api.content_negotiation import select_identify_response_format
from wild_catalog.api.dependencies import get_identify_pipeline, get_settings
from wild_catalog.api.errors import register_exception_handlers
from wild_catalog.api.logging import log_identify_request
from wild_catalog.api.multipart_request_mapper import create_multipart_form_command
from wild_catalog.api.openapi_schemas import IDENTIFY_REQUEST_OPENAPI_EXTRA
from wild_catalog.api.response_mapper import map_response
from wild_catalog.api.response_models import IdentifyResponse
from wild_catalog.api.simple_request_mapper import create_request_body_command
from wild_catalog.core.errors import (
    ContentLengthHeaderIsNotNumberError,
    ContentLengthHeaderMissingError,
    PayloadTooLargeError,
)
from wild_catalog.core.settings import Settings
from wild_catalog.identify_pipeline.identify_command import IdentifyCommand
from wild_catalog.identify_pipeline.identify_pipeline import IdentifyPipeline
from wild_catalog.range_data import import_inaturalist_open_range_data_if_missing

logger = logging.getLogger("uvicorn.error")


def preload_identify_pipeline() -> None:
    get_identify_pipeline()


def preload_inaturalist_open_range_data() -> None:
    settings = get_settings()
    import_inaturalist_open_range_data_if_missing(
        settings.range_store_database_path,
        settings.range_geopackage_download_dir,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ = app
    preload_inaturalist_open_range_data()
    preload_identify_pipeline()
    yield


app = FastAPI(title="Wild Catalog", lifespan=lifespan)
register_exception_handlers(app)


@app.middleware("http")
async def limit_content_length(request: Request, call_next):
    if request.method not in ["POST", "PUT", "PATCH"]:
        return await call_next(request)

    content_length = request.headers.get("content-length")

    try:
        if not content_length:
            raise ContentLengthHeaderMissingError()

        if not content_length.isdigit():
            raise ContentLengthHeaderIsNotNumberError()

        max_upload_bytes = Settings.from_env().max_upload_bytes
        if int(content_length) > max_upload_bytes:
            raise PayloadTooLargeError(max_upload_bytes)

    except (
        ContentLengthHeaderMissingError,
        ContentLengthHeaderIsNotNumberError,
        PayloadTooLargeError,
    ) as err:
        fastapi_exc = err.to_fastapi()
        return await http_exception_handler(request, fastapi_exc)

    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/identify",
    dependencies=[Depends(log_identify_request)],
    openapi_extra=IDENTIFY_REQUEST_OPENAPI_EXTRA,
    response_model=IdentifyResponse,
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

    result = await pipeline.execute(command, file)
    response_selection = select_identify_response_format(
        accept_header=accept_header,
        return_detected_images=result.return_detected_images,
    )

    response = map_response(
        result,
        response_selection,
    )

    return response

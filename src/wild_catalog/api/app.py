import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, BinaryIO

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.openapi.utils import get_openapi
from fastapi.responses import Response

from wild_catalog.api.content_negotiation import select_identify_response_format
from wild_catalog.api.dependencies import (
    get_identify_pipeline,
    get_settings,
    get_taxonomy_service,
)
from wild_catalog.api.errors import register_exception_handlers
from wild_catalog.api.logging import log_identify_request
from wild_catalog.api.multipart_request_mapper import create_multipart_form_command
from wild_catalog.api.openapi_schemas import IDENTIFY_REQUEST_OPENAPI_EXTRA
from wild_catalog.api.response_archive import IdentifyResponseArchive
from wild_catalog.api.response_mapper import map_identify_result_payload, map_response
from wild_catalog.api.response_models import (
    IdentifyResponse,
    TaxonomySearchItem,
    TaxonomySearchResponse,
)
from wild_catalog.api.simple_request_mapper import (
    create_request_body_command,
    parse_accept_language_header_preferences,
)
from wild_catalog.core.errors import (
    BadRequestError,
    ContentLengthHeaderIsNotNumberError,
    ContentLengthHeaderMissingError,
    PayloadTooLargeError,
)
from wild_catalog.core.settings import Settings
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.identify_pipeline.identify_command import IdentifyCommand
from wild_catalog.identify_pipeline.identify_pipeline import IdentifyPipeline
from wild_catalog.range_data import import_inaturalist_open_range_data_if_missing
from wild_catalog.taxonomy import import_taxonomy_archive_if_missing
from wild_catalog.taxonomy.taxonomy_service import SearchField, TaxonomyService

logger = logging.getLogger("uvicorn.error")


def preload_identify_pipeline() -> None:
    get_identify_pipeline()


def preload_inaturalist_open_range_data() -> None:
    settings = get_settings()
    import_inaturalist_open_range_data_if_missing(
        settings.range_store_database_path,
        settings.range_geopackage_download_dir,
    )


def preload_inaturalist_taxonomy_data() -> None:
    settings = get_settings()
    import_taxonomy_archive_if_missing(
        settings.taxonomy_store_database_path,
        settings.taxonomy_archive_download_dir,
        languages=settings.taxonomy_languages,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ = app
    preload_inaturalist_taxonomy_data()
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


@app.get(
    "/search",
    response_model=TaxonomySearchResponse,
    description="Searches taxonomy data. Results are limited to the top 20 matches.",
)
def search(
    taxonomy_service: Annotated[TaxonomyService, Depends(get_taxonomy_service)],
    query: Annotated[str | None, Query(description="Taxonomy search string.")] = None,
    q: Annotated[str | None, Query(description="Alias for query.")] = None,
    field: Annotated[
        SearchField | None,
        Query(description="Restrict search to common or scientific names."),
    ] = None,
    f: Annotated[
        SearchField | None,
        Query(description="Alias for field."),
    ] = None,
    latitude: Annotated[
        float | None,
        Query(
            description="GPS latitude used to filter results by known range presence.",
            ge=-90,
            le=90,
        ),
    ] = None,
    lat: Annotated[
        float | None,
        Query(
            description="Alias for latitude.",
            ge=-90,
            le=90,
        ),
    ] = None,
    longitude: Annotated[
        float | None,
        Query(
            description="GPS longitude used to filter results by known range presence.",
            ge=-180,
            le=180,
        ),
    ] = None,
    lng: Annotated[
        float | None,
        Query(
            description="Alias for longitude.",
            ge=-180,
            le=180,
        ),
    ] = None,
    accept_language: Annotated[
        str | None,
        Header(
            alias="accept-language",
            description="Language preference for common-name search and response names.",
        ),
    ] = None,
) -> TaxonomySearchResponse:
    if query is not None and q is not None:
        raise BadRequestError("Specify either query or q, not both.")

    if field is not None and f is not None:
        raise BadRequestError("Specify either field or f, not both.")

    search_query = query if query is not None else q
    search_field = field if field is not None else f
    gps_coordinates = _resolve_search_gps_coordinates(
        latitude=latitude,
        lat=lat,
        longitude=longitude,
        lng=lng,
    )
    if search_query is None or not search_query.strip():
        raise BadRequestError("Search query is required.")

    language_preferences = parse_accept_language_header_preferences(accept_language)
    if not language_preferences:
        language_preferences = ("en-US",)

    results = taxonomy_service.search(
        search_query,
        field=search_field,
        language_preferences=language_preferences,
        gps_coordinates=gps_coordinates,
    )

    items = [
        TaxonomySearchItem(
            taxonomy=list(result.taxonomy),
            taxonomy_rank_names=list(result.taxonomy_rank_names),
            taxonomy_common_names=list(result.taxonomy_common_names),
        )
        for result in results
    ]
    return TaxonomySearchResponse(total_items=len(items), items=items)


def _resolve_search_gps_coordinates(
    *,
    latitude: float | None,
    lat: float | None,
    longitude: float | None,
    lng: float | None,
) -> GpsCoordinates | None:
    if latitude is not None and lat is not None:
        raise BadRequestError("Specify either latitude or lat, not both.")

    if longitude is not None and lng is not None:
        raise BadRequestError("Specify either longitude or lng, not both.")

    resolved_latitude = latitude if latitude is not None else lat
    resolved_longitude = longitude if longitude is not None else lng

    if (resolved_latitude is None) != (resolved_longitude is None):
        raise BadRequestError("Specify both latitude and longitude, or neither.")

    if resolved_latitude is None or resolved_longitude is None:
        return None

    return GpsCoordinates(
        latitude=resolved_latitude,
        longitude=resolved_longitude,
    )


@app.post(
    "/identify",
    dependencies=[Depends(log_identify_request)],
    openapi_extra=IDENTIFY_REQUEST_OPENAPI_EXTRA,
    response_model=IdentifyResponse,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "multipart/mixed": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    },
                    "example": (
                        "Multipart response with an application/json part followed by "
                        "zero or more image/jpeg detected image parts."
                    ),
                }
            },
        },
        406: {
            "description": (
                "The requested response format is not acceptable. "
                "return_detected_images=true requires Accept: multipart/mixed."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "not_acceptable",
                            "message": (
                                "Requested detected images require multipart/mixed."
                            ),
                            "request_id": "request-id",
                        }
                    }
                }
            },
        }
    },
)
async def identify(
    request: Request,
    pipeline: Annotated[IdentifyPipeline, Depends(get_identify_pipeline)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept")
    command: IdentifyCommand
    file: BinaryIO

    if content_type.startswith("multipart/form-data"):
        command, file = await create_multipart_form_command(request)
    else:
        command, file = await create_request_body_command(request)

    select_identify_response_format(
        accept_header=accept_header,
        return_detected_images=command.return_detected_images,
    )

    result = await pipeline.execute(command, file)
    response_selection = select_identify_response_format(
        accept_header=accept_header,
        return_detected_images=result.return_detected_images,
    )
    payload = map_identify_result_payload(result)
    IdentifyResponseArchive(settings.response_archive_dir).store(result, payload)

    response = map_response(
        result,
        response_selection,
        payload=payload,
    )

    return response


def custom_openapi() -> dict[str, object]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    identify_response_content = (
        openapi_schema.get("paths", {})
        .get("/identify", {})
        .get("post", {})
        .get("responses", {})
        .get("200", {})
        .get("content", {})
    )

    if (
        isinstance(identify_response_content, dict)
        and "multipart/mixed" in identify_response_content
        and "application/json" in identify_response_content
    ):
        openapi_schema["paths"]["/identify"]["post"]["responses"]["200"]["content"] = {
            "multipart/mixed": identify_response_content["multipart/mixed"],
            "application/json": identify_response_content["application/json"],
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

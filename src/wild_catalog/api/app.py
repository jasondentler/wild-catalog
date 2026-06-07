from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.api.mappers import identify_request_to_command
from wild_catalog.api.multipart import build_multipart_response
from wild_catalog.api.request_models import IdentifyRequest
from wild_catalog.api.serializers import identify_result_to_json
from wild_catalog.pipeline.identify import IdentifyPipeline

app = FastAPI(title="Wild Catalog")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/identify")
async def identify(
    request: Request,
    image: Annotated[UploadFile, File()],
    payload: Annotated[str, Form()],
    pipeline: Annotated[IdentifyPipeline, Depends(get_identify_pipeline)],
) -> Response:
    try:
        identify_request = IdentifyRequest.model_validate_json(payload)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors()) from error

    identify_command = identify_request_to_command(identify_request)

    result = await run_in_threadpool(
        pipeline.identify,
        image.file,
        identify_command,
    )

    if identify_command.return_detected_images:
        return build_multipart_response(result, include_images=True)

    accept_header = request.headers.get("accept")
    if accept_header and "multipart/mixed" in accept_header:
        return build_multipart_response(result, include_images=False)

    return JSONResponse(content=identify_result_to_json(result))


import logging
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import Response

from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.api.errors import register_exception_handlers
from wild_catalog.api.logging import log_identify_request_middleware
from wild_catalog.api.request_models import IdentifyRequest
from wild_catalog.pipeline.identify_pipeline import IdentifyPipeline

# Set up your standard logger
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Wild Catalog")
register_exception_handlers(app)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/identify", dependencies=[Depends(log_identify_request_middleware)])
async def identify(
    request: Request,
    pipeline: Annotated[IdentifyPipeline, Depends(get_identify_pipeline)],
    image: Annotated[UploadFile, File()],
    payload: Annotated[IdentifyRequest | None, Form()] = None,
) -> Response:
    ...

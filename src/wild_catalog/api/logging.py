import logging
from typing import Annotated

from fastapi import File, Form, UploadFile

from wild_catalog.api.request_models import IdentifyRequest

logger = logging.getLogger("uvicorn.error")

async def log_identify_request_middleware(
    image: Annotated[UploadFile, File()],
    payload: Annotated[IdentifyRequest | None, Form()] = None,
) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return

    # Log Image Metadata
    if image:
        # Null-coalesce missing filenames or content types safely
        filename = image.filename or "untitled"
        content_type = image.content_type or "unknown"
        size = image.size or 0
        logger.debug(f"image: {filename}; type={content_type}; size={size:,} bytes")
    else:
        logger.debug("image: None")

    # Log Parsed Pydantic Payload
    if payload:
        logger.debug(f"Request payload: {payload.model_dump_json()}")
    else:
        logger.debug("Request payload: None")

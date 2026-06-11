import logging

from fastapi import Request, UploadFile

logger = logging.getLogger("uvicorn.error")


async def log_identify_request(request: Request) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return

    content_type = request.headers.get("content-type", "")
    __log_content_type(content_type)

    if content_type.startswith("multipart/form-data"):
        await __log_multipart_form_data(request)
    else:
        __log_single_part_upload(request)


def __log_content_type(content_type: str) -> None:
    logger.debug(f"Content-Type: {content_type or 'None'}")


async def __log_multipart_form_data(request: Request) -> None:
    form = await request.form()
    __log_image(form.get("image"))
    __log_payload(form.get("payload"))


def __log_image(image: UploadFile) -> None:
    if not image:
        logger.debug("image: None")
        return

    filename = image.filename or "untitled"
    content_type = image.content_type or "unknown"
    size = __format_size(image.size or 0)

    logger.debug(f"image.filename: {filename}")
    logger.debug(f"image.content_type: {content_type}")
    logger.debug(f"image.size: {size}")


def __log_payload(payload) -> None:
    if not payload:
        logger.debug("payload: None")
        return

    logger.debug(f"payload: {payload}")


def __log_single_part_upload(request: Request) -> None:
    filename = request.headers.get("x-filename")
    content_length = __format_size(request.headers.get("content-length"))
    logger.debug(f"x-filename: {filename}")
    logger.debug(f"content-length: {content_length} bytes")


def __format_size(size_bytes: int | str) -> str:
    if size_bytes is None:
        return "0 B"

    if isinstance(size_bytes, str):
        size_bytes = int(size_bytes)

    if size_bytes == 0:
        return "0 B"

    # Define the base-2 unit sizes
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(size_bytes)
    unit_index = 0

    # Divide by 1024 until the size is under 1024 or we run out of units
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"

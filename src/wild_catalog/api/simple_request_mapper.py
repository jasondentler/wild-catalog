from collections.abc import AsyncGenerator

from fastapi import Request

from wild_catalog.core.errors import (
    ContentLengthHeaderIsNotNumberError,
    InvalidContentLanguageError,
)
from wild_catalog.identify_pipeline.identify_command import IdentifyCommand


async def create_request_body_command(
    request: Request,
) -> tuple[IdentifyCommand, AsyncGenerator[bytes]]:
    original_filename: str | None = request.headers.get("x-filename", None)
    image_size_bytes: int | None
    content_length = request.headers.get("content-length")
    content_language = request.headers.get("content-language")

    if content_length and not content_length.isdigit():
        raise ContentLengthHeaderIsNotNumberError(
            debug_detail=f"Content-length was [{content_length}]"
        )

    image_size_bytes = int(content_length) if content_length is not None else None
    common_name_language = parse_content_language_header(content_language)

    return IdentifyCommand(
        original_filename=original_filename,
        image_size_bytes=image_size_bytes,
        common_name_language=common_name_language,
    ), request.stream()


def parse_content_language_header(content_language: str | None) -> str | None:
    if content_language is None:
        return None

    if content_language.strip() == "":
        raise InvalidContentLanguageError(
            debug_detail=f"Invalid content-language header [{content_language}]"
        )

    parsed_langs = []
    for item in content_language.split(","):
        parts = item.strip().split(";")
        tag = parts[0]
        q = 1.0  # Default weight

        if not tag:
            raise InvalidContentLanguageError(
                debug_detail=f"Invalid content-language header [{content_language}]"
            )

        if len(parts) > 1 and parts[1].startswith("q="):
            try:
                q = float(parts[1].split("=")[1])
            except ValueError as err:
                raise InvalidContentLanguageError(
                    debug_detail=f"Invalid content-language header [{content_language}]"
                ) from err

        parsed_langs.append((tag, q))

    if not parsed_langs:
        raise InvalidContentLanguageError(  # pragma: no cover
            debug_detail=f"Invalid content-language header [{content_language}]"
        )

    # Sort by weight descending
    parsed_langs.sort(key=lambda x: x[1], reverse=True)

    return parsed_langs[0][0]

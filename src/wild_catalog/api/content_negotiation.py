from dataclasses import dataclass
from enum import StrEnum


class ResponseFormat(StrEnum):
    JSON = "json"
    MULTIPART = "multipart"


@dataclass(frozen=True, slots=True)
class ResponseSelection:
    response_format: ResponseFormat
    include_images: bool


class NotAcceptableResponseError(ValueError):
    """Raised when the requested response cannot satisfy the Accept header."""


def select_identify_response_format(
    *,
    accept_header: str | None,
    return_detected_images: bool,
) -> ResponseSelection:
    accepted_media_types = _accepted_media_types(accept_header)

    if return_detected_images:
        if _accept_allows_multipart(
            accept_header=accept_header,
            accepted_media_types=accepted_media_types,
        ):
            return ResponseSelection(
                response_format=ResponseFormat.MULTIPART,
                include_images=True,
            )

        raise NotAcceptableResponseError(
            "return_detected_images=true requires an Accept header that allows "
            "multipart/mixed."
        )

    if "application/json" in accepted_media_types:
        return ResponseSelection(
            response_format=ResponseFormat.JSON,
            include_images=False,
        )

    if "multipart/mixed" in accepted_media_types:
        return ResponseSelection(
            response_format=ResponseFormat.MULTIPART,
            include_images=False,
        )

    return ResponseSelection(
        response_format=ResponseFormat.JSON,
        include_images=False,
    )


def _accept_allows_multipart(
    *,
    accept_header: str | None,
    accepted_media_types: set[str],
) -> bool:
    if accept_header is None or accept_header.strip() == "":
        return True

    return (
        "multipart/mixed" in accepted_media_types
        or "multipart/*" in accepted_media_types
        or "*/*" in accepted_media_types
    )


def _accepted_media_types(accept_header: str | None) -> set[str]:
    if accept_header is None:
        return set()

    media_types: set[str] = set()

    for item in accept_header.split(","):
        media_type = item.strip().lower().split(";", maxsplit=1)[0].strip()

        if media_type:
            media_types.add(media_type)

    return media_types

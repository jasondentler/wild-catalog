import asyncio

import pytest
from starlette.requests import Request

from wild_catalog.api.simple_request_mapper import (
    create_request_body_command,
    parse_content_language_header,
)
from wild_catalog.core.errors import (
    ContentLengthHeaderIsNotNumberError,
    InvalidContentLanguageError,
)


@pytest.mark.parametrize(
    "content_language, expected",
    [
        (None, None),
        ("en-US", "en-US"),
        ("es-MX, en-US;q=0.8", "es-MX"),
        ("en-US;q=0.8, es-MX;q=0.9", "es-MX"),
        ("en-US; q=0.8", "en-US"),
    ],
)
def test_parse_content_language_header_returns_best_match(
    content_language: str | None,
    expected: str | None,
) -> None:
    assert parse_content_language_header(content_language) == expected


@pytest.mark.parametrize(
    "content_language",
    [
        "",
        ",",
        " ;q=0.8",
        "en-US;q=bad",
        " ; q=0.8, ",
    ],
)
def test_parse_content_language_header_rejects_invalid_values(
    content_language: str,
) -> None:
    with pytest.raises(InvalidContentLanguageError):
        parse_content_language_header(content_language)


def test_create_request_body_command_rejects_invalid_content_language_header() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [(b"content-language", b"en-US;q=bad")],
        },
        receive,
    )

    with pytest.raises(InvalidContentLanguageError):
        asyncio.run(create_request_body_command(request))


def test_create_request_body_command_rejects_invalid_content_length() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [(b"content-length", b"abc")],
        },
        receive,
    )

    with pytest.raises(ContentLengthHeaderIsNotNumberError):
        asyncio.run(create_request_body_command(request))


def test_create_request_body_command_accepts_missing_headers() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [],
        },
        receive,
    )

    command, _ = asyncio.run(create_request_body_command(request))

    assert command.image_size_bytes is None

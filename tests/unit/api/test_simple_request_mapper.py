import asyncio

import pytest
from starlette.requests import Request

from wild_catalog.api.simple_request_mapper import (
    create_request_body_command,
    parse_accept_language_header,
    parse_accept_language_header_preferences,
)
from wild_catalog.core.errors import (
    ContentLengthHeaderIsNotNumberError,
    InvalidContentLanguageError,
)


@pytest.mark.parametrize(
    "accept_language, expected",
    [
        (None, None),
        ("en-US", "en-US"),
        ("es-MX, en-US;q=0.8", "es-MX"),
        ("en-US;q=0.8, es-MX;q=0.9", "es-MX"),
        ("en-US; q=0.8", "en-US"),
    ],
)
def test_parse_accept_language_header_returns_best_match(
    accept_language: str | None,
    expected: str | None,
) -> None:
    assert parse_accept_language_header(accept_language) == expected


def test_parse_accept_language_header_preferences_returns_weighted_order() -> None:
    assert parse_accept_language_header_preferences(
        "en-US;q=0.8, es-MX;q=0.9, fr-FR;q=0"
    ) == ("es-MX", "en-US")


@pytest.mark.parametrize(
    "accept_language",
    [
        "",
        ",",
        " ;q=0.8",
        "en-US;q=bad",
        "en-US;q=0",
        " ; q=0.8, ",
    ],
)
def test_parse_accept_language_header_rejects_invalid_values(
    accept_language: str,
) -> None:
    with pytest.raises(InvalidContentLanguageError):
        parse_accept_language_header(accept_language)


def test_create_request_body_command_rejects_invalid_accept_language_header() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [(b"accept-language", b"en-US;q=bad")],
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
    assert command.common_name_language == "en-US"


def test_create_request_body_command_uses_accept_language_header() -> None:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/identify",
            "headers": [(b"accept-language", b"en-US;q=0.8, es-MX;q=0.9")],
        },
        receive,
    )

    command, _ = asyncio.run(create_request_body_command(request))

    assert command.common_name_language == "es-MX"

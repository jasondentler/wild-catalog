import asyncio
from types import SimpleNamespace

from starlette.requests import Request

from wild_catalog.api.logging import log_identify_request


class DummyLogger:
    def __init__(self, *, debug_enabled: bool) -> None:
        self.debug_enabled = debug_enabled
        self.messages: list[str] = []

    def isEnabledFor(self, level: int) -> bool:  # noqa: N802
        return self.debug_enabled

    def debug(self, message: str) -> None:
        self.messages.append(message)


def make_request(*, content_type: str, body: bytes = b"", form=None) -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/identify",
        "headers": [(b"content-type", content_type.encode())],
    }
    request = Request(scope, receive)

    if form is not None:
        request._form = form  # type: ignore[attr-defined]

    return request


def test_log_identify_request_skips_logging_when_debug_disabled(monkeypatch) -> None:
    dummy_logger = DummyLogger(debug_enabled=False)
    monkeypatch.setattr("wild_catalog.api.logging.logger", dummy_logger)

    asyncio.run(
        log_identify_request(
            make_request(content_type="application/octet-stream", body=b"fake image bytes")
        )
    )

    assert dummy_logger.messages == []


def test_log_identify_request_logs_image_and_payload(monkeypatch) -> None:
    dummy_logger = DummyLogger(debug_enabled=True)
    monkeypatch.setattr("wild_catalog.api.logging.logger", dummy_logger)

    asyncio.run(
        log_identify_request(
            make_request(
                content_type="multipart/form-data; boundary=boundary",
                form={
                    "image": SimpleNamespace(
                        filename=None,
                        content_type=None,
                        size=None,
                    ),
                    "payload": '{"original_filename":"camera.jpg"}',
                },
            )
        )
    )

    assert dummy_logger.messages == [
        "Content-Type: multipart/form-data; boundary=boundary",
        "image.filename: untitled",
        "image.content_type: unknown",
        "image.size: 0 B",
        'payload: {"original_filename":"camera.jpg"}',
    ]


def test_log_identify_request_logs_missing_values(monkeypatch) -> None:
    dummy_logger = DummyLogger(debug_enabled=True)
    monkeypatch.setattr("wild_catalog.api.logging.logger", dummy_logger)

    asyncio.run(
        log_identify_request(
            make_request(content_type="application/octet-stream", body=b""),
        )
    )

    assert dummy_logger.messages == [
        "Content-Type: application/octet-stream",
        "x-filename: None",
        "content-length: 0 B bytes",
    ]

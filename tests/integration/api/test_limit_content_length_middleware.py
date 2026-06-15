import os

import pytest
from fastapi.testclient import TestClient

from wild_catalog.api.app import app
from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.core.settings import Settings
from wild_catalog.identify_pipeline.identify_result import IdentifyResult


class DummyPipeline:
    async def execute(self, command, file):
        return IdentifyResult(objects=())


def _set_max_upload_bytes(
    monkeypatch: pytest.MonkeyPatch,
    max_body_size: int,
) -> None:
    monkeypatch.setattr(
        "wild_catalog.api.app.Settings.from_env",
        lambda: Settings(max_upload_bytes=max_body_size),
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_limit_content_length_middleware_allows_payloads_within_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_max_upload_bytes(monkeypatch, max_body_size=4)
    app.dependency_overrides[get_identify_pipeline] = lambda: DummyPipeline()
    client = TestClient(app)

    try:
        response = client.post(
            "/identify",
            content=b"1234",
            headers={
                "content-type": "image/jpeg",
                "x-filename": "small.jpg",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_limit_content_length_middleware_rejects_payloads_over_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_max_upload_bytes(monkeypatch, max_body_size=4)
    client = TestClient(app)

    response = client.post(
        "/identify",
        content=b"12345",
        headers={
            "content-type": "image/jpeg",
            "x-filename": "too-large.jpg",
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "Uploaded file exceeds the configured size limit of 4 bytes."
    )

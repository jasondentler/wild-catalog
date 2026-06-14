import os

import pytest

from wild_catalog.wildlife_detection.device import get_torch_device


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)
def test_get_torch_device_returns_available_runtime_device() -> None:
    assert get_torch_device() in {"cpu", "cuda", "mps"}

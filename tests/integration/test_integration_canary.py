import os

import pytest


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute."
)
def test_integration_canary():
    assert True

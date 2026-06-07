import os

import pytest

pytestmark = pytest.mark.integration


requires_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_integration_suite
def test_integration_canary() -> None:
    assert True

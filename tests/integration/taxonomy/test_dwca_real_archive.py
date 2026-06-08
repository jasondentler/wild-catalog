import os
from pathlib import Path

import pytest

from wild_catalog.core.config import Settings
from wild_catalog.taxonomy.dwca import (
    download_taxonomy_dwca,
    load_taxonomy_store_from_dwca,
)

pytestmark = pytest.mark.integration

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_enabled_integration_suite
def test_load_real_taxonomy_dwca_if_present() -> None:
    archive_path = Path("data/taxonomy/taxonomy.dwca.zip")
    settings = Settings(taxonomy_dwca_path=archive_path)

    download_taxonomy_dwca(settings)

    store = load_taxonomy_store_from_dwca(archive_path)

    assert store.get_taxon(1) is not None

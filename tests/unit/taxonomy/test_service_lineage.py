import pytest

from wild_catalog.core.config import Settings
from wild_catalog.taxonomy.service import TaxonomyService
from wild_catalog.taxonomy.store import InMemoryTaxonomyStore
from wild_catalog.taxonomy.types import TaxonRecord


def test_build_lineage_returns_broad_to_specific_order() -> None:
    store = InMemoryTaxonomyStore(
        taxa_by_id={
            1: TaxonRecord(1, "Animalia", "kingdom", None),
            2: TaxonRecord(2, "Chordata", "phylum", 1),
            3: TaxonRecord(3, "Aves", "class", 2),
        }
    )
    service = TaxonomyService(Settings(), store=store)

    lineage = service._build_lineage(3)

    assert lineage.scientific_names == ("Animalia", "Chordata", "Aves")
    assert lineage.ranks == ("kingdom", "phylum", "class")


def test_build_lineage_rejects_parent_cycle() -> None:
    store = InMemoryTaxonomyStore(
        taxa_by_id={
            1: TaxonRecord(1, "Animalia", "kingdom", 2),
            2: TaxonRecord(2, "Chordata", "phylum", 1),
        }
    )
    service = TaxonomyService(Settings(), store=store)

    with pytest.raises(ValueError, match="cycle"):
        service._build_lineage(1)

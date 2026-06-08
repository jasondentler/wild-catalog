from wild_catalog.taxonomy.store import InMemoryTaxonomyStore
from wild_catalog.taxonomy.types import CommonNameRecord, TaxonRecord


def build_stub_taxonomy_store() -> InMemoryTaxonomyStore:
    taxa_by_id = {
        1: TaxonRecord(
            taxon_id=1,
            scientific_name="Animalia",
            rank="kingdom",
            parent_taxon_id=None,
        ),
        2: TaxonRecord(
            taxon_id=2,
            scientific_name="Chordata",
            rank="phylum",
            parent_taxon_id=1,
        ),
        3: TaxonRecord(
            taxon_id=3,
            scientific_name="Aves",
            rank="class",
            parent_taxon_id=2,
        ),
    }

    common_names_by_taxon_id = {
        1: (CommonNameRecord(taxon_id=1, locale="en-US", name="Animals"),),
        2: (CommonNameRecord(taxon_id=2, locale="en-US", name="Chordates"),),
        3: (CommonNameRecord(taxon_id=3, locale="en-US", name="Birds"),),
    }

    return InMemoryTaxonomyStore(
        taxa_by_id=taxa_by_id,
        common_names_by_taxon_id=common_names_by_taxon_id,
    )

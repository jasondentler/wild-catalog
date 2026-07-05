from pydantic import BaseModel


class TaxonomySearchItem(BaseModel):
    taxonomy: list[str]
    taxonomy_rank_names: list[str]
    taxonomy_common_names: list[str]


class TaxonomySearchResponse(BaseModel):
    total_items: int
    items: list[TaxonomySearchItem]

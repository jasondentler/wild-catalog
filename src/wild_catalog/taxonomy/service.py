from wild_catalog.core.config import Settings


class TaxonomyService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

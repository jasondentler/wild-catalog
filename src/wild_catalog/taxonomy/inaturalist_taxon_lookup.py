from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from typing import Protocol

import requests_cache

logger = logging.getLogger("uvicorn.error")

INATURALIST_TAXA_API_URL = "https://api.inaturalist.org/v2/taxa"

TaxonIdLookup = Callable[[Iterable[str]], Mapping[str, int]]


class TaxonLookupResponse(Protocol):
    def json(self) -> object: ...

    def raise_for_status(self) -> None: ...


class TaxonLookupSession(Protocol):
    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> TaxonLookupResponse: ...


class INaturalistActiveTaxonLookup:
    def __init__(
        self,
        *,
        api_url: str = INATURALIST_TAXA_API_URL,
        timeout_seconds: float = 10.0,
        session: TaxonLookupSession | None = None,
    ) -> None:
        self._api_url = api_url
        self._timeout_seconds = timeout_seconds
        self._session = session or requests_cache.CachedSession(backend="memory")
        self._taxon_id_by_scientific_name: dict[str, int | None] = {}

    def get_taxon_ids_by_scientific_names(
        self,
        scientific_names: Iterable[str],
    ) -> dict[str, int]:
        resolved: dict[str, int] = {}
        for scientific_name in sorted({name for name in scientific_names if name}):
            taxon_id = self._taxon_id_for_scientific_name(scientific_name)
            if taxon_id is not None:
                resolved[scientific_name] = taxon_id

        return resolved

    def _taxon_id_for_scientific_name(self, scientific_name: str) -> int | None:
        if scientific_name not in self._taxon_id_by_scientific_name:
            self._taxon_id_by_scientific_name[scientific_name] = (
                self._fetch_taxon_id_for_scientific_name(scientific_name)
            )

        return self._taxon_id_by_scientific_name[scientific_name]

    def _fetch_taxon_id_for_scientific_name(self, scientific_name: str) -> int | None:
        params = {
            "q": scientific_name,
            "is_active": "true",
            "rank": "species",
            "locale": "English",
            "fields": "id",
        }

        try:
            response = self._session.get(
                self._api_url,
                params=params,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - best-effort startup fallback.
            logger.warning(
                "Unable to resolve active iNaturalist taxon for %s: %s",
                scientific_name,
                exc,
            )
            return None

        if not isinstance(payload, Mapping):
            return None

        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return None

        first_result = results[0]
        if not isinstance(first_result, Mapping):
            return None

        try:
            return int(first_result["id"])
        except (KeyError, TypeError, ValueError):
            return None


def local_then_inaturalist_taxon_lookup(
    local_lookup: TaxonIdLookup,
    inaturalist_lookup: TaxonIdLookup | None = None,
) -> TaxonIdLookup:
    fallback_lookup = (
        inaturalist_lookup
        or INaturalistActiveTaxonLookup().get_taxon_ids_by_scientific_names
    )

    def lookup(scientific_names: Iterable[str]) -> dict[str, int]:
        requested_names = sorted({name for name in scientific_names if name})
        local_taxon_ids = dict(local_lookup(requested_names))
        missing_names = [name for name in requested_names if name not in local_taxon_ids]
        if not missing_names:
            return local_taxon_ids

        return {
            **local_taxon_ids,
            **dict(fallback_lookup(missing_names)),
        }

    return lookup

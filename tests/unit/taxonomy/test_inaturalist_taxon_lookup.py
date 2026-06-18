from collections.abc import Mapping

from wild_catalog.taxonomy import inaturalist_taxon_lookup as lookup_module
from wild_catalog.taxonomy.inaturalist_taxon_lookup import (
    INaturalistActiveTaxonLookup,
    local_then_inaturalist_taxon_lookup,
)


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _Session:
    def __init__(self, *payloads: object) -> None:
        self._payloads = list(payloads)
        self.requests: list[tuple[str, Mapping[str, str], float]] = []

    def get(self, url: str, *, params: Mapping[str, str], timeout: float) -> _Response:
        self.requests.append((url, params, timeout))
        return _Response(self._payloads.pop(0))


def test_inaturalist_active_taxon_lookup_resolves_species_taxon_id() -> None:
    session = _Session({"total_results": 1, "results": [{"id": 1289601}]})
    lookup = INaturalistActiveTaxonLookup(
        timeout_seconds=3.5,
        session=session,
    )

    taxon_ids = lookup.get_taxon_ids_by_scientific_names(
        ["Phalacrocorax brasilianus"]
    )

    assert taxon_ids == {"Phalacrocorax brasilianus": 1289601}
    assert len(session.requests) == 1
    url, params, timeout = session.requests[0]
    assert url == "https://api.inaturalist.org/v2/taxa"
    assert timeout == 3.5
    assert params == {
        "q": "Phalacrocorax brasilianus",
        "is_active": "true",
        "rank": "species",
        "locale": "English",
        "fields": "id",
    }


def test_inaturalist_active_taxon_lookup_caches_empty_and_successful_results() -> None:
    session = _Session(
        {"total_results": 0, "results": []},
        {"total_results": 1, "results": [{"id": 22}]},
    )
    lookup = INaturalistActiveTaxonLookup(session=session)

    assert lookup.get_taxon_ids_by_scientific_names(["Missing species"]) == {}
    assert lookup.get_taxon_ids_by_scientific_names(["Missing species"]) == {}
    assert lookup.get_taxon_ids_by_scientific_names(["Resolved species"]) == {
        "Resolved species": 22,
    }
    assert lookup.get_taxon_ids_by_scientific_names(["Resolved species"]) == {
        "Resolved species": 22,
    }
    assert len(session.requests) == 2


def test_inaturalist_active_taxon_lookup_uses_requests_cache_session_by_default(
    monkeypatch,
) -> None:
    session = _Session({"total_results": 1, "results": [{"id": 1289601}]})
    created_sessions = []

    def cached_session(*, backend):
        created_sessions.append({"backend": backend})
        return session

    monkeypatch.setattr(
        lookup_module.requests_cache,
        "CachedSession",
        cached_session,
    )
    lookup = INaturalistActiveTaxonLookup()

    assert lookup._fetch_taxon_id_for_scientific_name("Phalacrocorax brasilianus") == 1289601
    assert created_sessions == [{"backend": "memory"}]


def test_local_then_inaturalist_taxon_lookup_only_fetches_local_misses() -> None:
    fallback_requests = []

    def local_lookup(scientific_names):
        assert scientific_names == ["Agelaius phoeniceus", "Phalacrocorax brasilianus"]
        return {"Agelaius phoeniceus": 9744}

    def fallback_lookup(scientific_names):
        fallback_requests.append(list(scientific_names))
        return {"Phalacrocorax brasilianus": 1289601}

    lookup = local_then_inaturalist_taxon_lookup(local_lookup, fallback_lookup)

    assert lookup(["Phalacrocorax brasilianus", "Agelaius phoeniceus"]) == {
        "Agelaius phoeniceus": 9744,
        "Phalacrocorax brasilianus": 1289601,
    }
    assert fallback_requests == [["Phalacrocorax brasilianus"]]

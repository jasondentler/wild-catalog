from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from shapely import Polygon

from wild_catalog.core.types import GpsCoordinates
from wild_catalog.range_data import species_range_prior_service as service_module
from wild_catalog.range_data.class_index import ClassIndex
from wild_catalog.range_data.presence_cache import PresenceCache
from wild_catalog.range_data.species_range_prior_service import SpeciesRangePriorService


def test_species_range_prior_service_builds_sqlite_store_from_settings(monkeypatch) -> None:
    settings = SimpleNamespace(
        prior_epsilon=0.01,
        range_prior_cache_enabled=False,
        range_prior_cache_max_entries=10,
        range_prior_cache_h3_resolution=7,
        range_store_database_path=Path("data/range-data/inaturalist-open-range-store.sqlite"),
    )
    store = SimpleNamespace(marker="store")
    seen_paths = []

    monkeypatch.setattr(
        service_module,
        "SQLiteSpeciesRangeStore",
        lambda database_path: seen_paths.append(database_path) or store,
    )

    service = service_module.SpeciesRangePriorService(settings)

    assert service._store is store
    assert seen_paths == [settings.range_store_database_path]


def test_species_range_prior_service_uses_injected_store(monkeypatch) -> None:
    settings = SimpleNamespace(
        prior_epsilon=0.01,
        range_prior_cache_enabled=False,
        range_prior_cache_max_entries=10,
        range_prior_cache_h3_resolution=7,
        range_store_database_path=Path("data/range-data/inaturalist-open-range-store.sqlite"),
    )
    store = SimpleNamespace(marker="store")

    monkeypatch.setattr(
        service_module,
        "SQLiteSpeciesRangeStore",
        lambda database_path: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    service = service_module.SpeciesRangePriorService(settings, store=store)

    assert service._store is store


def test_generate_prior_mask_returns_all_ones_when_gps_is_missing() -> None:
    service = SpeciesRangePriorService(_settings(), store=_FakeStore([]))
    class_index = ClassIndex(
        id="inat21",
        taxon_id_by_class_id={0: 10, 1: 20},
    )

    result = service.generate_prior_mask(None, class_index)

    assert result.class_index_id == "inat21"
    assert torch.equal(result.values, torch.tensor([1.0, 1.0]))


def test_generate_prior_mask_applies_epsilon_to_absent_taxa() -> None:
    polygon = Polygon(
        [
            (-95.0, 29.0),
            (-94.0, 29.0),
            (-94.0, 30.0),
            (-95.0, 30.0),
            (-95.0, 29.0),
        ]
    )
    service = SpeciesRangePriorService(
        _settings(prior_epsilon=0.05),
        store=_FakeStore([(10, polygon.wkb), (30, polygon.wkb)]),
    )
    class_index = ClassIndex(
        id="inat21",
        taxon_id_by_class_id={0: 10, 1: 20, 2: 30},
    )

    result = service.generate_prior_mask(
        GpsCoordinates(latitude=29.5, longitude=-94.5),
        class_index,
    )

    assert result.class_index_id == "inat21"
    assert torch.equal(result.values, torch.tensor([1.0, 0.05, 1.0]))


def test_get_present_taxon_ids_returns_exact_point_membership() -> None:
    inside_polygon = Polygon(
        [
            (-95.0, 29.0),
            (-94.0, 29.0),
            (-94.0, 30.0),
            (-95.0, 30.0),
            (-95.0, 29.0),
        ]
    )
    outside_polygon = Polygon(
        [
            (-80.0, 40.0),
            (-79.0, 40.0),
            (-79.0, 41.0),
            (-80.0, 41.0),
            (-80.0, 40.0),
        ]
    )
    service = SpeciesRangePriorService(
        _settings(),
        store=_FakeStore([(10, inside_polygon.wkb), (20, outside_polygon.wkb)]),
    )

    result = service.get_present_taxon_ids(
        GpsCoordinates(latitude=29.5, longitude=-94.5),
    )

    assert result == {10}


def test_generate_prior_mask_uses_cached_presence_without_querying_store() -> None:
    cache = PresenceCache(max_entries=2)
    gps_coordinates = GpsCoordinates(latitude=29.5, longitude=-94.5)
    cache.put(
        PresenceCache.presence_cache_key(gps_coordinates, h3_resolution=7),
        {20},
    )
    store = _FakeStore([])
    service = SpeciesRangePriorService(
        _settings(range_prior_cache_enabled=True),
        store=store,
        cache=cache,
    )
    class_index = ClassIndex(
        id="inat21",
        taxon_id_by_class_id={0: 10, 1: 20},
    )

    result = service.generate_prior_mask(gps_coordinates, class_index)

    assert torch.equal(result.values, torch.tensor([0.01, 1.0]))
    assert store.point_queries == []


def test_get_present_taxon_ids_uses_cached_presence_without_querying_store() -> None:
    cache = PresenceCache(max_entries=2)
    gps_coordinates = GpsCoordinates(latitude=29.5, longitude=-94.5)
    cache.put(
        PresenceCache.presence_cache_key(gps_coordinates, h3_resolution=7),
        {20},
    )
    store = _FakeStore([])
    service = SpeciesRangePriorService(
        _settings(range_prior_cache_enabled=True),
        store=store,
        cache=cache,
    )

    result = service.get_present_taxon_ids(gps_coordinates)

    assert result == {20}
    assert store.point_queries == []


def test_generate_prior_mask_populates_cache_after_store_query() -> None:
    polygon = Polygon(
        [
            (-95.0, 29.0),
            (-94.0, 29.0),
            (-94.0, 30.0),
            (-95.0, 30.0),
            (-95.0, 29.0),
        ]
    )
    cache = PresenceCache(max_entries=2)
    gps_coordinates = GpsCoordinates(latitude=29.5, longitude=-94.5)
    service = SpeciesRangePriorService(
        _settings(range_prior_cache_enabled=True),
        store=_FakeStore([(10, polygon.wkb)]),
        cache=cache,
    )
    class_index = ClassIndex(
        id="inat21",
        taxon_id_by_class_id={0: 10},
    )

    result = service.generate_prior_mask(gps_coordinates, class_index)

    assert torch.equal(result.values, torch.tensor([1.0]))
    assert cache.get(PresenceCache.presence_cache_key(gps_coordinates, h3_resolution=7)) == {
        10
    }


def test_generate_prior_mask_rejects_non_contiguous_class_ids() -> None:
    service = SpeciesRangePriorService(_settings(), store=_FakeStore([]))
    class_index = ClassIndex(
        id="inat21",
        taxon_id_by_class_id={1: 10},
    )

    with pytest.raises(ValueError, match="contiguous class IDs"):
        service.generate_prior_mask(None, class_index)


def test_service_creates_cache_from_settings_when_not_injected() -> None:
    service = SpeciesRangePriorService(
        _settings(range_prior_cache_enabled=True, range_prior_cache_max_entries=3),
        store=_FakeStore([]),
    )

    assert isinstance(service._cache, PresenceCache)
    service._cache.put("first", {1})
    service._cache.put("second", {2})
    service._cache.put("third", {3})
    service._cache.put("fourth", {4})

    assert service._cache.get("first") is None
    assert service._cache.get("fourth") == {4}


class _FakeStore:
    def __init__(self, candidate_geometries):
        self._candidate_geometries = list(candidate_geometries)
        self.point_queries = []

    def get_candidate_geometries_for_point(self, *, latitude: float, longitude: float):
        self.point_queries.append((latitude, longitude))
        return list(self._candidate_geometries)

    def get_candidate_geometries_for_taxa_at_point(
        self,
        *,
        latitude: float,
        longitude: float,
        taxon_ids,
    ):
        _ = latitude, longitude
        requested_taxon_ids = set(taxon_ids)
        return [
            (taxon_id, geometry_wkb)
            for taxon_id, geometry_wkb in self._candidate_geometries
            if taxon_id in requested_taxon_ids
        ]


def _settings(
    *,
    prior_epsilon: float = 0.01,
    range_prior_cache_enabled: bool = False,
    range_prior_cache_max_entries: int = 10,
):
    return SimpleNamespace(
        prior_epsilon=prior_epsilon,
        range_prior_cache_enabled=range_prior_cache_enabled,
        range_prior_cache_max_entries=range_prior_cache_max_entries,
        range_prior_cache_h3_resolution=7,
        range_store_database_path=Path("data/range-data/inaturalist-open-range-store.sqlite"),
    )

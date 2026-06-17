from collections.abc import Iterable

import torch
from shapely import Point, from_wkb

from wild_catalog.core.settings import Settings
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.range_data.class_index import ClassIndex
from wild_catalog.range_data.presence_cache import PresenceCache
from wild_catalog.range_data.prior_mask import PriorMask
from wild_catalog.range_data.species_range_store import SpeciesRangeStore
from wild_catalog.range_data.sqlite_species_range_store import SQLiteSpeciesRangeStore


class SpeciesRangePriorService:
    def __init__(
        self,
        settings: Settings,
        store: SpeciesRangeStore | None = None,
        cache: PresenceCache | None = None,
    ) -> None:
        self._settings = settings
        self._epsilon = settings.prior_epsilon
        self._store = store or self._build_store(settings)
        self._cache = cache

        if self._cache is None and settings.range_prior_cache_enabled:
            self._cache = PresenceCache(
                max_entries=settings.range_prior_cache_max_entries,
            )

    def generate_prior_mask(
        self,
        gps_coordinates: GpsCoordinates | None,
        class_index: ClassIndex,
    ) -> PriorMask:
        self._validate_class_index(class_index)

        class_count = len(class_index.taxon_id_by_class_id)

        if gps_coordinates is None:
            return PriorMask(
                values=torch.ones(class_count, dtype=torch.float32),
                class_index_id=class_index.id,
            )

        present_taxon_ids = self._get_present_taxon_ids(gps_coordinates)

        values = torch.empty(class_count, dtype=torch.float32)

        for class_id in range(class_count):
            taxon_id = class_index.taxon_id_by_class_id[class_id]
            values[class_id] = 1.0 if taxon_id in present_taxon_ids else self._epsilon

        return PriorMask(
            values=values,
            class_index_id=class_index.id,
        )

    def _get_present_taxon_ids(
        self,
        gps_coordinates: GpsCoordinates,
    ) -> set[int]:
        cache_key = self._presence_cache_key(gps_coordinates)
        cached_present_taxon_ids = self._cache.get(cache_key) if self._cache else None

        if cached_present_taxon_ids is not None:
            return cached_present_taxon_ids

        candidate_geometries = self._store.get_candidate_geometries_for_point(
            latitude=gps_coordinates.latitude,
            longitude=gps_coordinates.longitude,
        )
        present_taxon_ids = self._get_present_taxon_ids_at_point(
            latitude=gps_coordinates.latitude,
            longitude=gps_coordinates.longitude,
            candidate_geometries=candidate_geometries,
        )

        if self._cache:
            self._cache.put(cache_key, present_taxon_ids)

        return present_taxon_ids

    def _presence_cache_key(self, gps_coordinates: GpsCoordinates) -> str:
        return PresenceCache.presence_cache_key(
            gps_coordinates,
            h3_resolution=self._settings.range_prior_cache_h3_resolution,
        )

    @staticmethod
    def _get_present_taxon_ids_at_point(
        *,
        latitude: float,
        longitude: float,
        candidate_geometries: Iterable[tuple[int, bytes]],
    ) -> set[int]:
        point = Point(longitude, latitude)
        present_taxon_ids: set[int] = set()

        for taxon_id, geometry_wkb in candidate_geometries:
            geometry = from_wkb(geometry_wkb)

            if geometry.covers(point):
                present_taxon_ids.add(taxon_id)

        return present_taxon_ids

    def _build_store(self, settings: Settings) -> SpeciesRangeStore:
        return SQLiteSpeciesRangeStore(settings.range_store_database_path)

    def close(self) -> None:
        close = getattr(self._store, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> "SpeciesRangePriorService":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _validate_class_index(class_index: ClassIndex) -> None:
        class_ids = set(class_index.taxon_id_by_class_id)
        expected_class_ids = set(range(len(class_ids)))

        if class_ids != expected_class_ids:
            raise ValueError(
                "ClassIndex taxon_id_by_class_id must contain contiguous class IDs "
                "from 0 to class_count - 1."
            )

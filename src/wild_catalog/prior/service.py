import torch

from wild_catalog.classifier.types import ClassIndex
from wild_catalog.core.config import Settings
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.cache import PresenceCache, presence_cache_key
from wild_catalog.prior.point_lookup import get_present_taxon_ids_at_point
from wild_catalog.prior.store import SpeciesRangeStore, SQLiteSpeciesRangeStore
from wild_catalog.prior.stub import StubSpeciesRangeStore
from wild_catalog.prior.types import PresenceResult, PriorMask


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
        _validate_class_index(class_index)

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

    def get_presence_for_taxa(
        self,
        gps_coordinates: GpsCoordinates | None,
        taxon_ids: set[int],
    ) -> PresenceResult:
        if gps_coordinates is None:
            return PresenceResult(
                is_present_by_taxon_id={taxon_id: True for taxon_id in taxon_ids}
            )

        present_taxon_ids = self._get_present_requested_taxon_ids(
            gps_coordinates,
            taxon_ids,
        )

        return PresenceResult(
            is_present_by_taxon_id={
                taxon_id: taxon_id in present_taxon_ids for taxon_id in taxon_ids
            }
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
        present_taxon_ids = get_present_taxon_ids_at_point(
            latitude=gps_coordinates.latitude,
            longitude=gps_coordinates.longitude,
            candidate_geometries=candidate_geometries,
        )

        if self._cache:
            self._cache.put(cache_key, present_taxon_ids)

        return present_taxon_ids

    def _get_present_requested_taxon_ids(
        self,
        gps_coordinates: GpsCoordinates,
        taxon_ids: set[int],
    ) -> set[int]:
        if not taxon_ids:
            return set()

        cache_key = self._presence_cache_key(gps_coordinates)
        cached_present_taxon_ids = self._cache.get(cache_key) if self._cache else None

        if cached_present_taxon_ids is not None:
            return cached_present_taxon_ids & taxon_ids

        if self._cache:
            return self._get_present_taxon_ids(gps_coordinates) & taxon_ids

        candidate_geometries = self._store.get_candidate_geometries_for_taxa_at_point(
            latitude=gps_coordinates.latitude,
            longitude=gps_coordinates.longitude,
            taxon_ids=taxon_ids,
        )
        return get_present_taxon_ids_at_point(
            latitude=gps_coordinates.latitude,
            longitude=gps_coordinates.longitude,
            candidate_geometries=candidate_geometries,
        )

    def _presence_cache_key(self, gps_coordinates: GpsCoordinates) -> str:
        return presence_cache_key(
            gps_coordinates,
            h3_resolution=self._settings.range_prior_cache_h3_resolution,
        )

    def _build_store(self, settings: Settings) -> SpeciesRangeStore:
        if settings.range_map_store_path is None:
            return StubSpeciesRangeStore()

        return SQLiteSpeciesRangeStore(settings.range_map_store_path)


def _validate_class_index(class_index: ClassIndex) -> None:
    class_ids = set(class_index.taxon_id_by_class_id)
    expected_class_ids = set(range(len(class_ids)))

    if class_ids != expected_class_ids:
        raise ValueError(
            "ClassIndex taxon_id_by_class_id must contain contiguous class IDs "
            "from 0 to class_count - 1."
        )

import torch

from wild_catalog.classifier.types import ClassIndex
from wild_catalog.core.config import Settings
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.h3_index import gps_coordinates_to_h3_cell
from wild_catalog.prior.store import SpeciesRangeStore, SQLiteSpeciesRangeStore
from wild_catalog.prior.stub import StubSpeciesRangeStore
from wild_catalog.prior.types import PresenceResult, PriorMask


class SpeciesRangePriorService:
    def __init__(
        self,
        settings: Settings,
        store: SpeciesRangeStore | None = None,
    ) -> None:
        self._settings = settings
        self._epsilon = settings.prior_epsilon
        self._store = store or self._build_store(settings)

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

        h3_cell = gps_coordinates_to_h3_cell(
            gps_coordinates,
            resolution=self._store.get_h3_resolution(),
        )
        present_taxon_ids = self._store.get_present_taxon_ids_for_cell(h3_cell)

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

        h3_cell = gps_coordinates_to_h3_cell(
            gps_coordinates,
            resolution=self._store.get_h3_resolution(),
        )

        return PresenceResult(
            is_present_by_taxon_id={
                taxon_id: self._store.contains_taxon_in_cell(
                    h3_cell=h3_cell,
                    taxon_id=taxon_id,
                )
                for taxon_id in taxon_ids
            }
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

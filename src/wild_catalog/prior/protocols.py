from typing import Protocol

from wild_catalog.classifier.types import ClassIndex
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.types import PresenceResult, PriorMask


class SpeciesRangePrior(Protocol):
    def generate_prior_mask(
        self,
        gps_coordinates: GpsCoordinates | None,
        class_index: ClassIndex,
    ) -> PriorMask:
        ...

    def get_presence_for_taxa(
        self,
        gps_coordinates: GpsCoordinates | None,
        taxon_ids: set[int],
    ) -> PresenceResult:
        ...

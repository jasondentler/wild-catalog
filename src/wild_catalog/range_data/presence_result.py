from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PresenceResult:
    is_present_by_taxon_id: Mapping[int, bool]

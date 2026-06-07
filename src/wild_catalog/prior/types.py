from collections.abc import Mapping
from dataclasses import dataclass

import torch


@dataclass(frozen=True, slots=True)
class PriorMask:
    values: torch.Tensor
    class_index_id: str


@dataclass(frozen=True, slots=True)
class PresenceResult:
    is_present_by_taxon_id: Mapping[int, bool]

from collections.abc import Mapping
from dataclasses import dataclass, field

import torch

from wild_catalog.range_data.class_index import ClassIndex


@dataclass(frozen=True, slots=True)
class RawClassifierOutput:
    probabilities: torch.Tensor
    class_index: ClassIndex
    label_by_class_id: Mapping[int, str] = field(default_factory=dict)

from dataclasses import dataclass

import torch


@dataclass(frozen=True, slots=True)
class PriorMask:
    values: torch.Tensor
    class_index_id: str

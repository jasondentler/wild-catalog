from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

import torch


@dataclass(frozen=True, slots=True)
class ClassIndex:
    id: str
    taxon_id_by_class_id: Mapping[int, int]
    scientific_name_by_class_id: Mapping[int, str] = field(default_factory=dict)
    taxonomy_path_by_class_id: Mapping[int, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClassifierMetadata:
    backend: str
    model_id: str
    class_count: int
    class_index_id: str
    output_type: Literal["logits", "probabilities"]
    taxonomy_source: str


@dataclass(frozen=True, slots=True)
class RawClassifierOutput:
    logits: torch.Tensor
    class_index: ClassIndex


@dataclass(frozen=True, slots=True)
class ClassPrediction:
    class_id: int
    confidence: float

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ClassIndex:
    id: str
    taxon_id_by_class_id: Mapping[int, int]
    scientific_name_by_class_id: Mapping[int, str] = field(default_factory=dict)
    taxonomy_path_by_class_id: Mapping[int, tuple[str, ...]] = field(default_factory=dict)

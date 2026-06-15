from collections.abc import Iterable

from wild_catalog.core.types import BoundingBox, Detection


class DetectionDeduplicator:
    def __init__(self, iou_threshold: float = 0.45) -> None:
        self._iou_threshold = iou_threshold

    def deduplicate(self, detections: Iterable[Detection]) -> list[Detection]:
        candidates = list(detections)
        selected_indexes: list[int] = []
        confidence_ordered_indexes = sorted(
            range(len(candidates)),
            key=lambda index: (-candidates[index].confidence, index),
        )

        for current_index in confidence_ordered_indexes:
            current_detection = candidates[current_index]

            if any(
                self._is_duplicate_detection(
                    current_detection,
                    candidates[selected_index],
                )
                for selected_index in selected_indexes
            ):
                continue

            selected_indexes.append(current_index)

        return [candidates[index] for index in sorted(selected_indexes)]

    def _has_compatible_class(self, first: Detection, second: Detection) -> bool:
        if first.class_id == second.class_id:
            return True

        first_label = self._normalize_label(first.label)
        second_label = self._normalize_label(second.label)
        return first_label is not None and first_label == second_label

    def _is_duplicate_detection(
        self,
        candidate: Detection,
        selected: Detection,
    ) -> bool:
        if not self._has_compatible_class(candidate, selected):
            return False

        return self.calculate_iou(candidate.box, selected.box) > self._iou_threshold

    def _normalize_label(self, label: str | None) -> str | None:
        if label is None:
            return None

        normalized = " ".join(label.casefold().split())
        return normalized or None

    @staticmethod
    def calculate_iou(first: BoundingBox, second: BoundingBox) -> float:
        intersection_width = max(
            0,
            min(first.xmax, second.xmax) - max(first.xmin, second.xmin),
        )
        intersection_height = max(
            0,
            min(first.ymax, second.ymax) - max(first.ymin, second.ymin),
        )
        intersection_area = intersection_width * intersection_height
        if intersection_area == 0:
            return 0.0

        first_area = (first.xmax - first.xmin) * (first.ymax - first.ymin)
        second_area = (second.xmax - second.xmin) * (second.ymax - second.ymin)
        return intersection_area / (first_area + second_area - intersection_area)

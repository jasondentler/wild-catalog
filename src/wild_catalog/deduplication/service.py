from collections.abc import Sequence

from wild_catalog.deduplication.iou import calculate_iou
from wild_catalog.detection.types import Detection


class DetectionDeduplicator:
    def __init__(self, iou_threshold: float = 0.45) -> None:
        if iou_threshold < 0.0 or iou_threshold > 1.0:
            raise ValueError("iou_threshold must be between 0.0 and 1.0.")

        self._iou_threshold = iou_threshold

    def filter_overlapping_detections(
        self,
        detections: Sequence[Detection],
    ) -> list[Detection]:
        kept: list[Detection] = []

        for detection in sorted(detections, key=lambda item: item.confidence, reverse=True):
            if any(
                detection.category == kept_detection.category
                and calculate_iou(detection.bounding_box, kept_detection.bounding_box)
                > self._iou_threshold
                for kept_detection in kept
            ):
                continue

            kept.append(detection)

        return kept

    def deduplicate(self, detections: Sequence[Detection]) -> list[Detection]:
        return self.filter_overlapping_detections(detections)

from collections.abc import Sequence

from wild_catalog.detection.types import Detection


class DetectionDeduplicator:
    def __init__(self, iou_threshold: float = 0.45) -> None:
        self._iou_threshold = iou_threshold

    def deduplicate(self, detections: Sequence[Detection]) -> list[Detection]:
        return list(detections)

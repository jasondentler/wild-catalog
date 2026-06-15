from collections.abc import AsyncGenerator
from io import BytesIO

from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.detection import Detection
from wild_catalog.core.settings import Settings
from wild_catalog.deduplicate_detections.detection_deduplicator import DetectionDeduplicator
from wild_catalog.pipeline.identify_command import IdentifyCommand
from wild_catalog.pipeline.identify_result import IdentifiedObject, IdentifyResult
from wild_catalog.pipeline.noop_wildlife_detector import NoopWildlifeDetector
from wild_catalog.pipeline.prediction import Prediction
from wild_catalog.wildlife_detection.detector import Detector


class IdentifyPipeline:
    def __init__(
        self,
        settings: Settings,
        conversion: ImageConversionService,
        wildlife_detector: Detector | None = None,
        *,
        detection_deduplicator: DetectionDeduplicator,
    ):
        self._settings = settings
        self._conversion = conversion
        self._wildlife_detector = wildlife_detector or NoopWildlifeDetector()
        self._detection_deduplicator = detection_deduplicator

    async def execute(
        self,
        command: IdentifyCommand,
        image_stream: AsyncGenerator[bytes],
    ) -> IdentifyResult:
        image_bytes = bytearray()
        async for chunk in image_stream:
            image_bytes.extend(chunk)

        converted = self._conversion.process_and_extract_metadata(
            image_file=BytesIO(bytes(image_bytes)),
            original_filename=command.original_filename,
            gps_coordinates_override=(
                command.exif_override.gps_coordinates if command.exif_override is not None else None
            ),
            captured_at_override=(
                command.exif_override.captured_at if command.exif_override is not None else None
            ),
        )

        normalized_image = getattr(converted, "image", converted)
        detections = self._wildlife_detector.detect(normalized_image)
        deduplicated_detections = self._detection_deduplicator.deduplicate(detections)

        identified_objects = tuple(
            self._map(detection) for detection in deduplicated_detections
        )

        return IdentifyResult(
            objects=identified_objects,
            gps_coordinates=getattr(converted, "gps_coordinates", None),
            return_detected_images=False,
        )

    def _map(self, detection: Detection) -> IdentifiedObject:
        label_taxonomy = (detection.label,) if detection.label is not None else ()
        prediction = Prediction(
            confidence=detection.confidence,
            is_present=False,
            taxonomy=label_taxonomy,
            taxonomy_common_names=label_taxonomy,
            class_id=detection.class_id,
        )

        return IdentifiedObject(
            detection.box,
            detection.box,
            (prediction,),
            None,
        )

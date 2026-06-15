import asyncio
from types import SimpleNamespace

from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.core.types import BoundingBox, Detection, GpsCoordinates
from wild_catalog.deduplicate_detections.detection_deduplicator import DetectionDeduplicator
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.identify_pipeline.identified_object import IdentifiedObject
from wild_catalog.identify_pipeline.identify_command import ExifOverride, IdentifyCommand
from wild_catalog.identify_pipeline.identify_pipeline import IdentifyPipeline
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.image_cropper.image_cropping import ImageCropper


class _Conversion:
    def __init__(self, result: object | None = None) -> None:
        self.calls = []
        self.result = result or SimpleNamespace()

    def process_and_extract_metadata(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _Detector:
    def __init__(self, detections: list[Detection]) -> None:
        self.detections = detections
        self.calls = []

    def detect(self, normalized_image):
        self.calls.append(normalized_image)
        return self.detections


def test_identify_pipeline_reads_stream_and_forwards_exif_override() -> None:
    async def run():
        conversion = _Conversion()
        pipeline = IdentifyPipeline(
            SimpleNamespace(),
            conversion,
            detection_deduplicator=DetectionDeduplicator(),
            detection_processing_pipeline=DetectionProcessingPipeline(
                ImageCropper(Settings())
            ),
        )
        command = IdentifyCommand(
            original_filename="image.jpg",
            exif_override=ExifOverride(
                gps_coordinates=GpsCoordinates(latitude=1.0, longitude=2.0),
                captured_at=None,
            ),
        )

        async def stream():
            yield b"abc"
            yield b"def"

        result = await pipeline.execute(command, stream())
        return result, conversion

    result, conversion = asyncio.run(run())

    assert result.objects == ()
    assert result.gps_coordinates is None
    assert conversion.calls[0]["original_filename"] == "image.jpg"
    assert conversion.calls[0]["image_file"].getvalue() == b"abcdef"
    assert conversion.calls[0]["gps_coordinates_override"] == GpsCoordinates(
        latitude=1.0,
        longitude=2.0,
    )


def test_identify_pipeline_deduplicates_detected_objects() -> None:
    async def run():
        image = Image.new("RGB", (100, 120), color=(255, 0, 0))
        low_confidence_duplicate = Detection(
            box=BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
            confidence=0.4,
            class_id=0,
            label="animal",
        )
        high_confidence_duplicate = Detection(
            box=BoundingBox(xmin=1, ymin=1, xmax=11, ymax=11),
            confidence=0.9,
            class_id=0,
            label="animal",
        )
        distinct_detection = Detection(
            box=BoundingBox(xmin=50, ymin=50, xmax=60, ymax=60),
            confidence=0.8,
            class_id=0,
            label="animal",
        )
        detector = _Detector(
            [
                low_confidence_duplicate,
                high_confidence_duplicate,
                distinct_detection,
            ]
        )
        conversion = _Conversion(
            SimpleNamespace(
                image=image,
                gps_coordinates=GpsCoordinates(latitude=3.0, longitude=4.0),
            )
        )
        pipeline = IdentifyPipeline(
            SimpleNamespace(),
            conversion,
            detector,
            detection_deduplicator=DetectionDeduplicator(),
            detection_processing_pipeline=DetectionProcessingPipeline(
                ImageCropper(Settings())
            ),
        )

        async def stream():
            yield b"abc"

        result = await pipeline.execute(
            IdentifyCommand(original_filename="image.jpg"),
            stream(),
        )
        return result, detector, image

    result, detector, image = asyncio.run(run())

    assert detector.calls == [image]
    assert result.gps_coordinates == GpsCoordinates(latitude=3.0, longitude=4.0)
    assert [obj.bounding_box for obj in result.objects] == [
        BoundingBox(xmin=1, ymin=1, xmax=11, ymax=11),
        BoundingBox(xmin=50, ymin=50, xmax=60, ymax=60),
    ]
    assert [obj.predictions[0].confidence for obj in result.objects] == [0.9, 0.8]


def test_identify_pipeline_uses_injected_detection_deduplicator() -> None:
    async def run():
        detection = Detection(
            box=BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
            confidence=0.9,
            class_id=0,
            label="animal",
        )
        detector = _Detector([detection])
        deduplicator_calls = []

        def deduplicate(detections):
            deduplicator_calls.append(detections)
            return []

        pipeline = IdentifyPipeline(
            SimpleNamespace(),
            _Conversion(),
            detector,
            detection_deduplicator=SimpleNamespace(deduplicate=deduplicate),
            detection_processing_pipeline=DetectionProcessingPipeline(
                ImageCropper(Settings())
            ),
        )

        async def stream():
            yield b"abc"

        result = await pipeline.execute(
            IdentifyCommand(original_filename="image.jpg"),
            stream(),
        )
        return result, deduplicator_calls, detector

    result, deduplicator_calls, detector = asyncio.run(run())

    assert deduplicator_calls == [detector.detections]
    assert result.objects == ()


def test_identify_pipeline_uses_injected_detection_processing_pipeline() -> None:
    async def run():
        image = Image.new("RGB", (100, 120), color=(255, 0, 0))
        discarded_detection = Detection(
            box=BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
            confidence=0.4,
            class_id=0,
            label="animal",
        )
        retained_detection = Detection(
            box=BoundingBox(xmin=1, ymin=1, xmax=11, ymax=11),
            confidence=0.9,
            class_id=0,
            label="animal",
        )
        detector = _Detector([discarded_detection, retained_detection])
        processing_calls = []
        conversion = _Conversion(SimpleNamespace(image=image))

        def process(received_image, detection):
            processing_calls.append((received_image, detection))
            return IdentifiedObject(
                bounding_box=detection.box,
                bounding_box_with_margin=detection.box,
                predictions=(
                    Prediction(
                        confidence=detection.confidence,
                        class_id=detection.class_id,
                        taxonomy=(detection.label,) if detection.label is not None else (),
                        taxonomy_common_names=(
                            (detection.label,) if detection.label is not None else ()
                        ),
                    ),
                ),
                cropped_image=received_image,
            )

        pipeline = IdentifyPipeline(
            SimpleNamespace(),
            conversion,
            detector,
            detection_deduplicator=DetectionDeduplicator(),
            detection_processing_pipeline=SimpleNamespace(process=process),
        )

        async def stream():
            yield b"abc"

        result = await pipeline.execute(
            IdentifyCommand(original_filename="image.jpg"),
            stream(),
        )
        return result, processing_calls, retained_detection, image

    result, processing_calls, retained_detection, image = asyncio.run(run())

    assert processing_calls == [(image, retained_detection)]
    assert result.objects[0].bounding_box == retained_detection.box

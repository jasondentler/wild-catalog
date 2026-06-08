from typing import BinaryIO

from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.deduplication.service import DetectionDeduplicator
from wild_catalog.detection.protocols import ObjectDetector
from wild_catalog.pipeline.models import IdentifyCommand, IdentifyResult
from wild_catalog.prior.protocols import SpeciesRangePrior
from wild_catalog.taxonomy.protocols import TaxonomyServiceProtocol


class IdentifyPipeline:
    def __init__(
        self,
        settings: Settings,
        converter: ImageConversionService,
        detector: ObjectDetector,
        deduplicator: DetectionDeduplicator,
        cropper: ImageCropper,
        prior_service: SpeciesRangePrior,
        classifier: SpeciesClassifier,
        conditioner: LogitConditioner,
        taxonomy_service: TaxonomyServiceProtocol,
    ) -> None:
        self._settings = settings
        self._converter = converter
        self._detector = detector
        self._deduplicator = deduplicator
        self._cropper = cropper
        self._prior_service = prior_service
        self._classifier = classifier
        self._conditioner = conditioner
        self._taxonomy_service = taxonomy_service

    def identify(self, image_file: BinaryIO, command: IdentifyCommand) -> IdentifyResult:
        return IdentifyResult(objects=())

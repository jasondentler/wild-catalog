from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.detection.protocols import ObjectDetector


class IdentifyPipeline:
    def __init__(
        self,
        detector: ObjectDetector,
        classifier: SpeciesClassifier,
    ) -> None:
        self._detector = detector
        self._classifier = classifier

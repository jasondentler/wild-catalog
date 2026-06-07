from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.core.config import Settings


def build_classifier(settings: Settings) -> SpeciesClassifier:
    raise NotImplementedError("Classifier registry is not implemented yet.")

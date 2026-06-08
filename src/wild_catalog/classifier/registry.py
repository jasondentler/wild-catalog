from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.classifier.stub import StubSpeciesClassifier
from wild_catalog.core.config import Settings


def build_classifier(settings: Settings) -> SpeciesClassifier:
    if settings.classifier_backend == "stub":
        return StubSpeciesClassifier()

    if settings.classifier_backend == "birder-inat21":
        from wild_catalog.classifier.birder import BirderSpeciesClassifier

        return BirderSpeciesClassifier(settings)

    raise ValueError(f"Unknown classifier backend: {settings.classifier_backend}")

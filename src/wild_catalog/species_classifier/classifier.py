from wild_catalog.species_classifier.birder_species_classifier import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODELS_DIR,
    BirderSpeciesClassifier,
)
from wild_catalog.species_classifier.classifier_base import Classifier
from wild_catalog.species_classifier.raw_classifier_output import RawClassifierOutput

SpeciesClassifier = BirderSpeciesClassifier

__all__ = [
    "DEFAULT_MODEL_NAME",
    "DEFAULT_MODELS_DIR",
    "BirderSpeciesClassifier",
    "Classifier",
    "RawClassifierOutput",
    "SpeciesClassifier",
]

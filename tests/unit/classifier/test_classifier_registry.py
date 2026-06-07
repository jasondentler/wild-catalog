import pytest

from wild_catalog.classifier.registry import build_classifier
from wild_catalog.core.config import Settings


def test_classifier_registry_is_placeholder() -> None:
    with pytest.raises(NotImplementedError, match="Classifier registry"):
        build_classifier(Settings())

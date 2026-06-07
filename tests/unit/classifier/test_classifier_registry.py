import pytest

from wild_catalog.classifier.registry import build_classifier
from wild_catalog.classifier.stub import StubSpeciesClassifier
from wild_catalog.core.config import Settings


def test_build_classifier_returns_stub_classifier() -> None:
    classifier = build_classifier(Settings(classifier_backend="stub"))

    assert isinstance(classifier, StubSpeciesClassifier)


def test_build_classifier_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown classifier backend"):
        build_classifier(Settings(classifier_backend="does-not-exist"))


def test_build_classifier_fails_clearly_for_unimplemented_birder() -> None:
    with pytest.raises(NotImplementedError, match="Birder iNat21 classifier backend"):
        build_classifier(Settings(classifier_backend="birder-inat21"))

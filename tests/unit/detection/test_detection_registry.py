import pytest

from wild_catalog.core.config import Settings
from wild_catalog.detection.grounding_dino import GroundingDinoObjectDetector
from wild_catalog.detection.registry import build_detector
from wild_catalog.detection.stub import StubObjectDetector


def test_build_detector_returns_stub_detector() -> None:
    detector = build_detector(Settings(detector_backend="stub"))

    assert isinstance(detector, StubObjectDetector)


def test_build_detector_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown detector backend"):
        build_detector(Settings(detector_backend="does-not-exist"))


def test_build_detector_returns_grounding_dino_detector() -> None:
    detector = build_detector(Settings(detector_backend="grounding-dino"))

    assert isinstance(detector, GroundingDinoObjectDetector)

import pytest

from wild_catalog.core.config import Settings
from wild_catalog.detection.registry import build_detector


def test_detector_registry_is_placeholder() -> None:
    with pytest.raises(NotImplementedError, match="Detector registry"):
        build_detector(Settings())

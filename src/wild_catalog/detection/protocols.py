from typing import Protocol

from PIL import Image

from wild_catalog.detection.types import Detection


class ObjectDetector(Protocol):
    def locate_objects(self, image: Image.Image) -> list[Detection]:
        ...

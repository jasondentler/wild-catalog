from PIL import Image

from wild_catalog.detection.types import Detection


class StubObjectDetector:
    def locate_objects(self, image: Image.Image) -> list[Detection]:
        return []

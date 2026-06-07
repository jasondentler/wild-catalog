from typing import BinaryIO

from PIL import Image

from wild_catalog.core.config import Settings


class ImageConversionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def convert(self, image_file: BinaryIO) -> Image.Image:
        return Image.open(image_file)

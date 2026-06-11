from io import BytesIO

from PIL import Image, ImageOps

from wild_catalog.conversion.converters.converter import Converter
from wild_catalog.conversion.exceptions import InvalidImageError


class PillowConverter(Converter):
    def convert(self, file_bytes: bytes) -> Image.Image:
        try:
            with Image.open(BytesIO(file_bytes)) as image:
                return ImageOps.exif_transpose(image).convert("RGB")
        except Exception as exc:
            raise InvalidImageError("Unable to decode standard image.") from exc

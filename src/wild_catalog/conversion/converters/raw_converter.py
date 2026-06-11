from tempfile import NamedTemporaryFile

import rawpy
from PIL import Image

from wild_catalog.conversion.converters.converter import Converter
from wild_catalog.conversion.exceptions import InvalidImageError


class RawConverter(Converter):
    def convert(self, file_bytes: bytes) -> Image.Image:
        try:
            with NamedTemporaryFile() as temp_file:
                temp_file.write(file_bytes)
                temp_file.flush()

                with rawpy.imread(temp_file.name) as raw:
                    rgb_array = raw.postprocess(use_camera_wb=True)

            return Image.fromarray(rgb_array).convert("RGB")
        except Exception as exc:
            raise InvalidImageError("Unable to decode RAW image.") from exc

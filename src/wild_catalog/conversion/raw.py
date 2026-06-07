from tempfile import NamedTemporaryFile

import rawpy
from PIL import Image

from wild_catalog.conversion.exceptions import ImageTooLargeError, InvalidImageError
from wild_catalog.conversion.format_sniffing import RAW_FORMATS, ImageFormat


def decode_raw_image(
    file_bytes: bytes,
    *,
    detected_format: ImageFormat,
    max_image_pixels: int,
) -> Image.Image:
    if detected_format not in RAW_FORMATS:
        raise InvalidImageError(f"{detected_format} is not a RAW format.")

    try:
        with NamedTemporaryFile(suffix=f".{detected_format.value}") as temp_file:
            temp_file.write(file_bytes)
            temp_file.flush()

            with rawpy.imread(temp_file.name) as raw:
                rgb_array = raw.postprocess(use_camera_wb=True)

        height, width = rgb_array.shape[:2]
        if width * height > max_image_pixels:
            raise ImageTooLargeError(
                f"Decoded RAW image has {width * height} pixels, "
                f"which exceeds limit {max_image_pixels}."
            )

        return Image.fromarray(rgb_array).convert("RGB")
    except ImageTooLargeError:
        raise
    except Exception as exc:
        raise InvalidImageError("Unable to decode RAW image.") from exc

from io import BytesIO

from PIL import Image, ImageOps

from wild_catalog.conversion.exceptions import ImageTooLargeError, InvalidImageError
from wild_catalog.conversion.format_sniffing import ImageFormat

STANDARD_FORMATS = {
    ImageFormat.JPEG,
    ImageFormat.PNG,
    ImageFormat.WEBP,
}


def decode_standard_image(
    file_bytes: bytes,
    *,
    max_image_pixels: int,
) -> Image.Image:
    try:
        with Image.open(BytesIO(file_bytes)) as image:
            image = ImageOps.exif_transpose(image)

            width, height = image.size
            if width * height > max_image_pixels:
                raise ImageTooLargeError(
                    f"Decoded image has {width * height} pixels, "
                    f"which exceeds limit {max_image_pixels}."
                )

            return image.convert("RGB")
    except ImageTooLargeError:
        raise
    except Exception as exc:
        raise InvalidImageError("Unable to decode standard image.") from exc

from collections.abc import Sequence

from PIL import Image


def ensure_rgb_crops(cropped_images: Sequence[Image.Image]) -> list[Image.Image]:
    return [image if image.mode == "RGB" else image.convert("RGB") for image in cropped_images]

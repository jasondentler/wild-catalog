from PIL import Image

from wild_catalog.classifier.transforms import ensure_rgb_crops


def test_ensure_rgb_crops_preserves_rgb_images() -> None:
    image = Image.new("RGB", (10, 10))

    result = ensure_rgb_crops([image])

    assert result[0] is image
    assert result[0].mode == "RGB"


def test_ensure_rgb_crops_converts_non_rgb_images() -> None:
    image = Image.new("L", (10, 10))

    result = ensure_rgb_crops([image])

    assert result[0].mode == "RGB"

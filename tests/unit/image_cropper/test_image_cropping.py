from PIL import Image

from wild_catalog.core.bounding_box import BoundingBox
from wild_catalog.core.detection import Detection
from wild_catalog.core.settings import Settings
from wild_catalog.image_cropper.image_cropping import ImageCropper


def test_calculate_margin_px_uses_minimum_margin_when_ratio_is_small() -> None:
    cropper = ImageCropper(
        Settings(
            crop_margin_ratio=0.1,
            crop_margin_min_px=8,
        )
    )

    assert cropper._calculate_margin_px(10) == 8


def test_calculate_margin_px_rounds_up_ratio_based_margin() -> None:
    cropper = ImageCropper(
        Settings(
            crop_margin_ratio=0.1,
            crop_margin_min_px=1,
        )
    )

    assert cropper._calculate_margin_px(25) == 3


def test_calculate_margin_box_expands_box_with_configured_margin() -> None:
    cropper = ImageCropper(
        Settings(
            crop_margin_ratio=0.1,
            crop_margin_min_px=8,
        )
    )
    original_box = BoundingBox(xmin=20, ymin=30, xmax=40, ymax=60)

    result = cropper._calculate_margin_box(
        image_width=100,
        image_height=120,
        original_box=original_box,
    )

    assert result == BoundingBox(xmin=12, ymin=22, xmax=48, ymax=68)


def test_calculate_margin_box_clamps_to_image_bounds() -> None:
    cropper = ImageCropper(
        Settings(
            crop_margin_ratio=0.25,
            crop_margin_min_px=8,
        )
    )
    original_box = BoundingBox(xmin=1, ymin=2, xmax=10, ymax=12)

    result = cropper._calculate_margin_box(
        image_width=15,
        image_height=14,
        original_box=original_box,
    )

    assert result == BoundingBox(xmin=0, ymin=0, xmax=15, ymax=14)


def test_crop_returns_crop_result_with_margin_box_and_image() -> None:
    cropper = ImageCropper(
        Settings(
            crop_margin_ratio=0.1,
            crop_margin_min_px=8,
        )
    )
    image = Image.new("RGB", (100, 120), color=(255, 0, 0))
    detection = Detection(
        box=BoundingBox(xmin=20, ymin=30, xmax=40, ymax=60),
        confidence=0.9,
        class_id=1,
        label="animal",
    )

    result = cropper.crop(image, detection)

    assert result.original_box == detection.box
    assert result.box_with_margin == BoundingBox(xmin=12, ymin=22, xmax=48, ymax=68)
    assert result.cropped_image.size == (36, 46)
    assert result.cropped_image.mode == "RGB"


def test_crop_image_converts_non_rgb_images_to_rgb() -> None:
    cropper = ImageCropper(
        Settings(
            crop_margin_ratio=0.1,
            crop_margin_min_px=8,
        )
    )
    image = Image.new("RGBA", (4, 4), color=(10, 20, 30, 40))

    result = cropper._crop_image(
        image,
        BoundingBox(xmin=1, ymin=1, xmax=3, ymax=3),
    )

    assert result.mode == "RGB"
    assert result.size == (2, 2)

"""Image crop extraction service."""

from __future__ import annotations

from math import ceil

from PIL import Image

from wild_catalog.core.bounding_box import BoundingBox
from wild_catalog.core.detection import Detection
from wild_catalog.core.settings import Settings
from wild_catalog.image_cropper.crop_result import CropResult


class ImageCropper:
    def __init__(self, settings: Settings):
        self._margin_ratio = settings.crop_margin_ratio
        self._margin_min_px = settings.crop_margin_min_px

    def crop(self, image: Image.Image, detection: Detection) -> CropResult:
        image_width, image_height = image.size

        box_with_margin = self._calculate_margin_box(
            image_width,
            image_height,
            detection.box,
        )

        crop_image = self._crop_image(image, box_with_margin)
        return CropResult(
            original_box=detection.box,
            box_with_margin=box_with_margin,
            cropped_image=crop_image,
        )

    def _calculate_margin_px(self, box_dimension: int) -> int:
        return max(self._margin_min_px, ceil(box_dimension * self._margin_ratio))

    def _calculate_margin_box(
        self,
        image_width: int,
        image_height: int,
        original_box: BoundingBox,
    ) -> BoundingBox:
        horizontal_margin = self._calculate_margin_px(original_box.width)
        vertical_margin = self._calculate_margin_px(original_box.height)
        xmin = max(0, original_box.xmin - horizontal_margin)
        ymin = max(0, original_box.ymin - vertical_margin)
        xmax = min(image_width, original_box.xmax + horizontal_margin)
        ymax = min(image_height, original_box.ymax + vertical_margin)

        return BoundingBox(
            xmin=xmin,
            ymin=ymin,
            xmax=xmax,
            ymax=ymax,
        )

    def _crop_image(
        self,
        image: Image.Image,
        box_with_margin: BoundingBox,
    ) -> Image.Image:
        cropped_image = image.crop(
            (
                box_with_margin.xmin,
                box_with_margin.ymin,
                box_with_margin.xmax,
                box_with_margin.ymax,
            )
        )
        if cropped_image.mode != "RGB":
            cropped_image = cropped_image.convert("RGB")

        return cropped_image

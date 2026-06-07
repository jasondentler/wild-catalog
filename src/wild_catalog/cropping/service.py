from wild_catalog.core.types import BoundingBox


class ImageCropper:
    def __init__(self, margin_ratio: float) -> None:
        self._margin_ratio = margin_ratio

    def add_margin(self, box: BoundingBox, image_width: int, image_height: int) -> BoundingBox:
        margin_x = round(box.width * self._margin_ratio)
        margin_y = round(box.height * self._margin_ratio)

        return BoundingBox(
            xmin=max(0, box.xmin - margin_x),
            ymin=max(0, box.ymin - margin_y),
            xmax=min(image_width, box.xmax + margin_x),
            ymax=min(image_height, box.ymax + margin_y),
        )

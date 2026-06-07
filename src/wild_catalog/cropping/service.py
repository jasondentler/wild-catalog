from PIL import Image

from wild_catalog.core.types import BoundingBox
from wild_catalog.cropping.types import CropResult
from wild_catalog.detection.types import Detection


class ImageCropper:
    def __init__(self, margin_ratio: float) -> None:
        self._margin_ratio = margin_ratio

    def add_margin(self, box: BoundingBox, image_width: int, image_height: int) -> BoundingBox:
        margin_x = int(box.width * self._margin_ratio)
        margin_y = int(box.height * self._margin_ratio)

        return BoundingBox(
            xmin=max(0, box.xmin - margin_x),
            ymin=max(0, box.ymin - margin_y),
            xmax=min(image_width, box.xmax + margin_x),
            ymax=min(image_height, box.ymax + margin_y),
        )

    def extract_target_regions(
        self,
        image: Image.Image,
        detections: list[Detection],
    ) -> list[CropResult]:
        results: list[CropResult] = []
        image_width, image_height = image.size

        for index, detection in enumerate(detections):
            box = detection.bounding_box
            crop_box = self.add_margin(
                box=box,
                image_width=image_width,
                image_height=image_height,
            )

            crop_image = image.crop(
                (
                    crop_box.xmin,
                    crop_box.ymin,
                    crop_box.xmax,
                    crop_box.ymax,
                )
            )

            results.append(
                CropResult(
                    index=index,
                    detection=detection,
                    bounding_box=box,
                    bounding_box_with_margin=crop_box,
                    image=crop_image,
                )
            )

        return results

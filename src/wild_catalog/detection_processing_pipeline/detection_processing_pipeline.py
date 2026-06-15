from PIL import Image

from wild_catalog.core.types import Detection
from wild_catalog.identify_pipeline.identified_object import IdentifiedObject
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.image_cropper.image_cropping import ImageCropper


class DetectionProcessingPipeline:
    def __init__(self, cropper: ImageCropper) -> None:
        self._cropper = cropper

    def process(self, image: Image.Image, detection: Detection) -> IdentifiedObject:
        crop_result = self._cropper.crop(image, detection)
        label_taxonomy = (detection.label,) if detection.label is not None else ()
        prediction = Prediction(
            confidence=detection.confidence,
            is_present=False,
            taxonomy=label_taxonomy,
            taxonomy_common_names=label_taxonomy,
            class_id=detection.class_id,
        )

        return IdentifiedObject(
            crop_result.original_box,
            crop_result.box_with_margin,
            (prediction,),
            crop_result.cropped_image,
        )

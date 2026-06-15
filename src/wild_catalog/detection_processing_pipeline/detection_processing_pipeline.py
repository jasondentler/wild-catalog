from PIL import Image

from wild_catalog.core.types import Detection
from wild_catalog.identify_pipeline.identified_object import IdentifiedObject
from wild_catalog.image_cropper.image_cropping import ImageCropper
from wild_catalog.species_classifier.classifier_base import Classifier


class DetectionProcessingPipeline:
    def __init__(self, cropper: ImageCropper, classifier: Classifier) -> None:
        self._cropper = cropper
        self._classifier = classifier

    def process(self, image: Image.Image, detection: Detection) -> IdentifiedObject:
        crop_result = self._cropper.crop(image, detection)
        predictions = tuple(self._classifier.classify(crop_result.cropped_image))

        return IdentifiedObject(
            crop_result.original_box,
            crop_result.box_with_margin,
            predictions,
            crop_result.cropped_image,
        )

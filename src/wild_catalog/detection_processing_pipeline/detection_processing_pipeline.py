from PIL import Image

from wild_catalog.core.types import Detection, GpsCoordinates
from wild_catalog.identify_pipeline.identified_object import IdentifiedObject
from wild_catalog.image_cropper.image_cropping import ImageCropper
from wild_catalog.logit_conditioning.logit_conditioner import LogitConditioner
from wild_catalog.range_data.species_range_prior_service import SpeciesRangePriorService
from wild_catalog.species_classifier.classifier_base import Classifier


class DetectionProcessingPipeline:
    def __init__(
        self,
        cropper: ImageCropper,
        classifier: Classifier,
        *,
        range_prior_service: SpeciesRangePriorService | None = None,
        logit_conditioner: LogitConditioner | None = None,
    ) -> None:
        self._cropper = cropper
        self._classifier = classifier
        self._range_prior_service = range_prior_service
        self._logit_conditioner = logit_conditioner

    def process(
        self,
        image: Image.Image,
        detection: Detection,
        gps_coordinates: GpsCoordinates | None = None,
    ) -> IdentifiedObject:
        crop_result = self._cropper.crop(image, detection)
        predictions = tuple(
            self._predict(
                crop_result.cropped_image,
                gps_coordinates,
            )
        )

        return IdentifiedObject(
            crop_result.original_box,
            crop_result.box_with_margin,
            predictions,
            crop_result.cropped_image,
        )

    def _predict(
        self,
        cropped_image: Image.Image,
        gps_coordinates: GpsCoordinates | None,
    ):
        if gps_coordinates is None or self._range_prior_service is None:
            return self._classifier.classify(cropped_image)

        if self._logit_conditioner is None:
            return self._classifier.classify(cropped_image)

        raw_output = self._classifier.classify_raw(cropped_image)
        prior_mask = self._range_prior_service.generate_prior_mask(
            gps_coordinates,
            raw_output.class_index,
        )

        return self._logit_conditioner.apply_geographic_prior(
            raw_output,
            prior_mask,
        )[0]

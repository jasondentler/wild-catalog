from typing import BinaryIO

from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.deduplication.service import DetectionDeduplicator
from wild_catalog.detection.protocols import ObjectDetector
from wild_catalog.pipeline.models import (
    IdentifiedObject,
    IdentifyCommand,
    IdentifyResult,
)
from wild_catalog.prior.protocols import SpeciesRangePrior
from wild_catalog.taxonomy.protocols import TaxonomyServiceProtocol


class IdentifyPipeline:
    def __init__(
        self,
        settings: Settings,
        converter: ImageConversionService,
        detector: ObjectDetector,
        deduplicator: DetectionDeduplicator,
        cropper: ImageCropper,
        prior_service: SpeciesRangePrior,
        classifier: SpeciesClassifier,
        conditioner: LogitConditioner,
        taxonomy_service: TaxonomyServiceProtocol,
    ) -> None:
        self._settings = settings
        self._converter = converter
        self._detector = detector
        self._deduplicator = deduplicator
        self._cropper = cropper
        self._prior_service = prior_service
        self._classifier = classifier
        self._conditioner = conditioner
        self._taxonomy_service = taxonomy_service

    def identify(self, image_file: BinaryIO, command: IdentifyCommand) -> IdentifyResult:
        converted = self._converter.process_and_extract_metadata(
            image_file=image_file,
            original_filename=command.original_filename,
            gps_coordinates_override=(
                command.exif_override.gps_coordinates
                if command.exif_override is not None
                else None
            ),
            captured_at_override=(
                command.exif_override.captured_at
                if command.exif_override is not None
                else None
            ),
        )

        detections = self._detector.locate_objects(converted.image)
        deduplicated_detections = self._deduplicator.deduplicate(detections)
        limited_detections = deduplicated_detections[: self._settings.max_detections]

        crop_results = self._cropper.extract_target_regions(
            image=converted.image,
            detections=limited_detections,
        )

        if not crop_results:
            return IdentifyResult(objects=())

        classifier_output = self._classifier.predict_species(
            [crop.image for crop in crop_results]
        )
        prior_mask = self._prior_service.generate_prior_mask(
            gps_coordinates=converted.gps_coordinates,
            class_index=classifier_output.class_index,
        )
        predictions_by_crop = self._conditioner.apply_geographic_prior(
            classifier_output=classifier_output,
            prior_mask=prior_mask,
        )

        taxon_ids = {
            classifier_output.class_index.taxon_id_by_class_id[prediction.class_id]
            for crop_predictions in predictions_by_crop
            for prediction in crop_predictions
        }
        presence = self._prior_service.get_presence_for_taxa(
            gps_coordinates=converted.gps_coordinates,
            taxon_ids=taxon_ids,
        )

        identified_objects: list[IdentifiedObject] = []

        for crop, crop_predictions in zip(
            crop_results,
            predictions_by_crop,
            strict=True,
        ):
            enriched_predictions = self._taxonomy_service.enrich_predictions(
                predictions=crop_predictions,
                class_index=classifier_output.class_index,
                common_name_language=command.common_name_language,
                presence_by_taxon_id=presence.is_present_by_taxon_id,
            )

            identified_objects.append(
                IdentifiedObject(
                    bounding_box=crop.bounding_box,
                    bounding_box_with_margin=crop.bounding_box_with_margin,
                    gps_coordinates=converted.gps_coordinates,
                    predictions=tuple(enriched_predictions),
                    cropped_image=(
                        crop.image if command.return_detected_images else None
                    ),
                )
            )

        return IdentifyResult(objects=tuple(identified_objects))

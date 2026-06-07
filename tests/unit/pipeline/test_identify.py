from wild_catalog.classifier.types import ClassifierMetadata, ClassIndex, RawClassifierOutput
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.deduplication.service import DetectionDeduplicator
from wild_catalog.pipeline.identify import IdentifyPipeline
from wild_catalog.prior.service import SpeciesRangePriorService
from wild_catalog.taxonomy.service import TaxonomyService


class DummyDetector:
    def locate_objects(self, image):
        return []


class DummyClassifier:
    @property
    def metadata(self) -> ClassifierMetadata:
        return ClassifierMetadata(
            backend="dummy",
            model_id="dummy-model",
            class_count=1,
            class_index_id="dummy-index",
            output_type="logits",
            taxonomy_source="dummy-taxonomy",
        )

    def predict_species(self, cropped_images):
        return RawClassifierOutput(
            logits=[],
            class_index=ClassIndex(
                id="dummy-index",
                taxon_id_by_class_id={0: 1},
            ),
        )


def test_identify_pipeline_stores_protocol_dependencies() -> None:
    detector = DummyDetector()
    classifier = DummyClassifier()
    settings = Settings()

    pipeline = IdentifyPipeline(
        settings=settings,
        converter=ImageConversionService(settings),
        detector=detector,
        deduplicator=DetectionDeduplicator(),
        cropper=ImageCropper(margin_ratio=settings.crop_margin_ratio),
        prior_service=SpeciesRangePriorService(settings),
        classifier=classifier,
        conditioner=LogitConditioner(
            gamma=settings.prior_gamma,
            epsilon=settings.prior_epsilon,
            top_k=settings.classifier_top_k,
        ),
        taxonomy_service=TaxonomyService(settings),
    )

    assert pipeline._detector is detector
    assert pipeline._classifier is classifier

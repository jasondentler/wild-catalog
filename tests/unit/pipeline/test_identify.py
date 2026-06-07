from wild_catalog.classifier.types import ClassifierMetadata, ClassIndex, RawClassifierOutput
from wild_catalog.pipeline.identify import IdentifyPipeline


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

    pipeline = IdentifyPipeline(detector=detector, classifier=classifier)

    assert pipeline._detector is detector
    assert pipeline._classifier is classifier

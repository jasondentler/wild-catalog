from wild_catalog.classifier.types import (
    ClassifierMetadata,
    ClassIndex,
    ClassPrediction,
    RawClassifierOutput,
)


def test_classifier_types_capture_raw_output() -> None:
    class_index = ClassIndex(id="test-index", taxon_id_by_class_id={7: 42})
    output = RawClassifierOutput(logits=[], class_index=class_index)
    prediction = ClassPrediction(class_id=7, confidence=0.8)
    metadata = ClassifierMetadata(
        backend="dummy",
        model_id="dummy-model",
        class_count=1,
        class_index_id="test-index",
        output_type="logits",
        taxonomy_source="dummy-taxonomy",
    )

    assert output.class_index.taxon_id_by_class_id[7] == 42
    assert prediction.class_id == 7
    assert metadata.output_type == "logits"

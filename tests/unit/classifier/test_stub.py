import torch
from PIL import Image

from wild_catalog.classifier.stub import StubSpeciesClassifier


def test_stub_classifier_metadata() -> None:
    classifier = StubSpeciesClassifier()

    metadata = classifier.metadata

    assert metadata.backend == "stub"
    assert metadata.model_id == "stub"
    assert metadata.class_count == 3
    assert metadata.class_index_id == "stub"
    assert metadata.output_type == "logits"
    assert metadata.taxonomy_source == "stub"


def test_stub_classifier_returns_one_logit_row_per_crop() -> None:
    classifier = StubSpeciesClassifier()
    crops = [
        Image.new("RGB", (10, 10)),
        Image.new("RGB", (20, 20)),
    ]

    output = classifier.predict_species(crops)

    assert output.class_index.id == "stub"
    assert output.logits.shape == (2, 3)


def test_stub_classifier_returns_float32_logits() -> None:
    classifier = StubSpeciesClassifier()
    crops = [Image.new("RGB", (10, 10))]

    output = classifier.predict_species(crops)

    assert output.logits.dtype == torch.float32

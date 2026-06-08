import sys
from types import SimpleNamespace

import pytest
import torch
from PIL import Image

from wild_catalog.classifier.birder import BirderSpeciesClassifier
from wild_catalog.core.config import Settings


def test_birder_classifier_metadata_placeholder() -> None:
    classifier = BirderSpeciesClassifier(Settings())

    metadata = classifier.metadata

    assert metadata.backend == "birder"
    assert metadata.model_id == "hieradet_d_small_dino-v2-inat21"
    assert metadata.class_count == 10_000
    assert metadata.class_index_id == "inat21"
    assert metadata.output_type == "logits"
    assert metadata.taxonomy_source == "inat21"


def test_birder_classifier_predict_species_returns_logits_with_fake_loader(monkeypatch) -> None:
    class FakeModel(torch.nn.Module):
        def forward(self, batch: torch.Tensor) -> torch.Tensor:
            return torch.ones((batch.shape[0], 2), dtype=torch.float32)

    def fake_transform(image: Image.Image) -> torch.Tensor:
        assert image.mode == "RGB"
        return torch.zeros((3, 8, 8), dtype=torch.float32)

    def fake_loader(*args, **kwargs):
        return (
            FakeModel(),
            SimpleNamespace(class_to_idx={"100 cormorant": 0, "200 heron": 1}),
            fake_transform,
        )

    monkeypatch.setitem(
        sys.modules,
        "birder",
        SimpleNamespace(load_pretrained_model_and_transform=fake_loader),
    )
    classifier = BirderSpeciesClassifier(Settings(classifier_batch_size=1))

    output = classifier.predict_species(
        [
            Image.new("L", (10, 10)),
            Image.new("RGB", (10, 10)),
        ]
    )

    assert output.logits.shape == (2, 2)
    assert output.logits.dtype == torch.float32
    assert output.class_index.id == "inat21"
    assert output.class_index.taxon_id_by_class_id == {0: 100, 1: 200}
    assert classifier.metadata.class_count == 2


def test_birder_classifier_load_failure_is_clear(monkeypatch) -> None:
    def fake_loader(*args, **kwargs):
        raise OSError("missing weights")

    monkeypatch.setitem(
        sys.modules,
        "birder",
        SimpleNamespace(load_pretrained_model_and_transform=fake_loader),
    )
    classifier = BirderSpeciesClassifier(Settings())

    with pytest.raises(RuntimeError, match="Unable to load Birder model"):
        classifier.predict_species([Image.new("RGB", (10, 10))])

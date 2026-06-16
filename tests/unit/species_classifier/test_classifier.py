import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.species_classifier.classifier import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODELS_DIR,
    BirderSpeciesClassifier,
    Classifier,
    SpeciesClassifier,
)


def test_classifier_interface_requires_classify_implementation() -> None:
    with pytest.raises(TypeError):
        Classifier()


def test_species_classifier_default_alias_uses_birder_species_classifier() -> None:
    assert SpeciesClassifier is BirderSpeciesClassifier


def test_birder_species_classifier_loads_default_model() -> None:
    loaded = {}
    model = SimpleNamespace(marker="model")
    model_info = SimpleNamespace(
        class_to_idx={
            "mallard": 0,
            "american robin": 1,
        }
    )
    transform = SimpleNamespace(marker="transform")

    def model_loader(*args, **kwargs):
        loaded["args"] = args
        loaded["kwargs"] = kwargs
        return model, model_info, transform

    classifier = BirderSpeciesClassifier(
        Settings(species_classifier_top_k=1),
        device="cpu",
        model_loader=model_loader,
        infer_image=lambda *args, **kwargs: (np.array([[0.9, 0.1]]), None),
    )

    assert classifier.model is model
    assert classifier.transform is transform
    assert classifier.class_to_idx == model_info.class_to_idx
    assert loaded == {
        "args": (DEFAULT_MODEL_NAME,),
        "kwargs": {
            "inference": True,
            "device": classifier.device,
            "progress_bar": False,
        },
    }


def test_birder_species_classifier_uses_lazy_birder_imports(monkeypatch) -> None:
    model = SimpleNamespace(marker="model")
    model_info = SimpleNamespace(class_to_idx={"mallard": 0})
    transform = SimpleNamespace(marker="transform")
    loaded = []

    birder_module = ModuleType("birder")
    birder_module.__path__ = []
    birder_conf_module = ModuleType("birder.conf")
    birder_net_module = ModuleType("birder.net")
    birder_inference_module = ModuleType("birder.inference")
    birder_classification_module = ModuleType("birder.inference.classification")
    birder_conf_settings = SimpleNamespace(MODELS_DIR=None)

    def load_pretrained_model_and_transform(*args, **kwargs):
        loaded.append((args, kwargs))
        return model, model_info, transform

    def infer_image(*args, **kwargs):
        return np.array([[0.9]]), None

    birder_module.load_pretrained_model_and_transform = load_pretrained_model_and_transform
    birder_conf_module.settings = birder_conf_settings
    birder_classification_module.infer_image = infer_image
    monkeypatch.setitem(sys.modules, "birder", birder_module)
    monkeypatch.setitem(sys.modules, "birder.conf", birder_conf_module)
    monkeypatch.setitem(sys.modules, "birder.net", birder_net_module)
    monkeypatch.setitem(sys.modules, "birder.inference", birder_inference_module)
    monkeypatch.setitem(
        sys.modules,
        "birder.inference.classification",
        birder_classification_module,
    )

    classifier = BirderSpeciesClassifier(
        Settings(species_classifier_top_k=1),
        device="cpu",
    )

    predictions = classifier.classify(Image.new("RGB", (8, 8)))

    assert loaded[0][0] == (DEFAULT_MODEL_NAME,)
    assert loaded[0][1]["inference"] is True
    assert loaded[0][1]["device"] == classifier.device
    assert birder_conf_settings.MODELS_DIR == DEFAULT_MODELS_DIR
    assert predictions[0].taxonomy == ("mallard",)


def test_birder_species_classifier_returns_top_k_predictions() -> None:
    model = SimpleNamespace(marker="model")
    model_info = SimpleNamespace(
        class_to_idx={
            "mallard": 0,
            "american robin": 1,
            "canada goose": 2,
        }
    )
    transform = SimpleNamespace(marker="transform")
    calls = []

    def infer_image(*args, **kwargs):
        calls.append((args, kwargs))
        return np.array([[0.12, 0.78, 0.43]]), None

    classifier = BirderSpeciesClassifier(
        Settings(species_classifier_top_k=2),
        device="cpu",
        model=model,
        model_info=model_info,
        transform=transform,
        infer_image=infer_image,
    )

    predictions = classifier.classify(Image.new("RGBA", (8, 8), (1, 2, 3, 4)))

    assert calls[0][0][0] is model
    assert calls[0][0][1].mode == "RGB"
    assert calls[0][0][2] is transform
    assert calls[0][1] == {"device": classifier.device}
    assert [prediction.class_id for prediction in predictions] == [1, 2]
    assert [prediction.confidence for prediction in predictions] == [0.78, 0.43]
    assert [prediction.taxonomy for prediction in predictions] == [
        ("american robin",),
        ("canada goose",),
    ]
    assert [prediction.taxonomy_common_names for prediction in predictions] == [
        ("american robin",),
        ("canada goose",),
    ]
    assert all(prediction.is_present for prediction in predictions)


def test_birder_species_classifier_uses_numeric_label_when_class_is_unknown() -> None:
    classifier = BirderSpeciesClassifier(
        Settings(species_classifier_top_k=1),
        device="cpu",
        model=SimpleNamespace(),
        model_info=SimpleNamespace(class_to_idx={}),
        transform=SimpleNamespace(),
        infer_image=lambda *args, **kwargs: (np.array([[0.2, 0.9]]), None),
    )

    predictions = classifier.classify(Image.new("RGB", (8, 8)))

    assert predictions[0].class_id == 1
    assert predictions[0].taxonomy == ("1",)

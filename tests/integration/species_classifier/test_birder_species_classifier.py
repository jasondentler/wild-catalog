from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.species_classifier.classifier import (
    DEFAULT_MODEL_NAME,
    BirderSpeciesClassifier,
)

SAMPLE_IMAGE = Path("sample-images/20260402-IMG_7906.jpg")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
        reason="Skipping integration test suite. Run 'make test' to execute.",
    ),
]


@pytest.fixture(scope="module")
def classifier() -> BirderSpeciesClassifier:
    return BirderSpeciesClassifier(
        Settings(species_classifier_top_k=5),
        device="cpu",
    )


def test_birder_species_classifier_runs_against_sample_image(
    classifier: BirderSpeciesClassifier,
) -> None:
    with Image.open(SAMPLE_IMAGE) as image:
        predictions = classifier.classify(image)

    assert classifier.model_name == DEFAULT_MODEL_NAME
    assert len(predictions) == 5
    assert all(isinstance(prediction, Prediction) for prediction in predictions)
    assert [prediction.confidence for prediction in predictions] == sorted(
        (prediction.confidence for prediction in predictions),
        reverse=True,
    )

    for prediction in predictions:
        assert 0 <= prediction.confidence <= 1
        assert prediction.is_present is True
        assert prediction.class_id >= 0
        assert prediction.taxonomy
        assert prediction.taxonomy_common_names == prediction.taxonomy

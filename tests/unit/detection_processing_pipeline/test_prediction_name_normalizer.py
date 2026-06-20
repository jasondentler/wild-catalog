import pytest

from wild_catalog.detection_processing_pipeline.prediction_name_normalizer import (
    PredictionNameNormalizer,
)
from wild_catalog.identify_pipeline.prediction import Prediction


def test_prediction_name_normalizer_capitalizes_common_names_at_all_ranks() -> None:
    result = PredictionNameNormalizer().normalize_prediction(
        Prediction(
            taxonomy=("Animalia", "Agelaius", "phoeniceus"),
            taxonomy_common_names=(
                "animals",
                "blackbirds and orioles",
                "black-bellied bewick's wren",
            ),
            taxonomy_rank_names=("kingdom", "genus", "species"),
        )
    )

    assert result.taxonomy_common_names == (
        "Animals",
        "Blackbirds And Orioles",
        "Black-Bellied Bewick's Wren",
    )


def test_prediction_name_normalizer_uses_rank_for_scientific_name_case() -> None:
    result = PredictionNameNormalizer().normalize_prediction(
        Prediction(
            taxonomy=("animalia", "agelaius", "PHOENICEUS", "BOREALIS"),
            taxonomy_rank_names=("kingdom", "genus", "species", "subspecies"),
        )
    )

    assert result.taxonomy == (
        "Animalia",
        "Agelaius",
        "phoeniceus",
        "borealis",
    )


def test_prediction_name_normalizer_requires_rank_metadata_for_scientific_names() -> None:
    with pytest.raises(ValueError):
        PredictionNameNormalizer().normalize_prediction(
            Prediction(
                taxonomy=("Animalia", "Agelaius"),
                taxonomy_rank_names=("kingdom",),
            )
        )

import pytest
import torch

from wild_catalog.logit_conditioning.logit_conditioner import LogitConditioner
from wild_catalog.range_data.class_index import ClassIndex
from wild_catalog.range_data.prior_mask import PriorMask
from wild_catalog.species_classifier.raw_classifier_output import RawClassifierOutput


def test_apply_geographic_prior_converts_probabilities_to_log_space() -> None:
    raw_output = RawClassifierOutput(
        probabilities=torch.tensor([[0.65, 0.30, 0.05]]),
        class_index=ClassIndex(
            id="inat21",
            taxon_id_by_class_id={0: 100, 1: 200, 2: 300},
            taxonomy_path_by_class_id={
                0: ("tricolored blackbird",),
                1: ("red-winged blackbird",),
                2: ("yellow-headed blackbird",),
            },
        ),
    )
    prior_mask = PriorMask(
        values=torch.tensor([0.01, 1.0, 0.01]),
        class_index_id="inat21",
    )

    result = LogitConditioner(gamma=2.0, epsilon=1e-12, top_k=2).apply_geographic_prior(
        raw_output,
        prior_mask,
    )

    assert [prediction.class_id for prediction in result[0]] == [1, 0]
    assert result[0][0].taxonomy == ("red-winged blackbird",)
    assert result[0][0].taxonomy_common_names == ("red-winged blackbird",)
    assert result[0][0].taxon_id == 200
    assert result[0][0].is_present is True
    assert result[0][1].is_present is False


def test_apply_geographic_prior_rejects_mismatched_class_index() -> None:
    raw_output = RawClassifierOutput(
        probabilities=torch.tensor([[1.0]]),
        class_index=ClassIndex(id="first", taxon_id_by_class_id={0: 100}),
    )
    prior_mask = PriorMask(values=torch.tensor([1.0]), class_index_id="second")

    with pytest.raises(ValueError, match="class index"):
        LogitConditioner(gamma=1.0, epsilon=1e-12, top_k=1).apply_geographic_prior(
            raw_output,
            prior_mask,
        )


def test_apply_geographic_prior_rejects_mask_length_mismatch() -> None:
    raw_output = RawClassifierOutput(
        probabilities=torch.tensor([[0.5, 0.5]]),
        class_index=ClassIndex(id="inat21", taxon_id_by_class_id={0: 100, 1: 200}),
    )
    prior_mask = PriorMask(values=torch.tensor([1.0]), class_index_id="inat21")

    with pytest.raises(ValueError, match="length"):
        LogitConditioner(gamma=1.0, epsilon=1e-12, top_k=1).apply_geographic_prior(
            raw_output,
            prior_mask,
        )


def test_apply_geographic_prior_returns_empty_batches() -> None:
    raw_output = RawClassifierOutput(
        probabilities=torch.empty((0, 2)),
        class_index=ClassIndex(id="inat21", taxon_id_by_class_id={0: 100, 1: 200}),
    )
    prior_mask = PriorMask(values=torch.tensor([1.0, 1.0]), class_index_id="inat21")

    assert (
        LogitConditioner(gamma=1.0, epsilon=1e-12, top_k=1).apply_geographic_prior(
            raw_output,
            prior_mask,
        )
        == []
    )

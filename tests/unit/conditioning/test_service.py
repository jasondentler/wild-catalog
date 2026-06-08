import pytest
import torch

from wild_catalog.classifier.types import ClassIndex, RawClassifierOutput
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.prior.types import PriorMask


def test_logit_conditioner_rejects_negative_gamma() -> None:
    with pytest.raises(ValueError, match="gamma"):
        LogitConditioner(gamma=-1.0, epsilon=0.01, top_k=3)


def test_logit_conditioner_rejects_non_positive_epsilon() -> None:
    with pytest.raises(ValueError, match="epsilon"):
        LogitConditioner(gamma=1.0, epsilon=0.0, top_k=3)


def test_logit_conditioner_rejects_non_positive_top_k() -> None:
    with pytest.raises(ValueError, match="top_k"):
        LogitConditioner(gamma=1.0, epsilon=0.01, top_k=0)


def test_apply_geographic_prior_rejects_class_index_mismatch() -> None:
    conditioner = LogitConditioner(gamma=1.0, epsilon=0.01, top_k=3)
    prior_mask = PriorMask(
        values=torch.tensor([1.0, 1.0, 1.0]),
        class_index_id="other",
    )

    with pytest.raises(ValueError, match="class index"):
        conditioner.apply_geographic_prior(
            classifier_output=make_classifier_output(torch.tensor([[1.0, 2.0, 3.0]])),
            prior_mask=prior_mask,
        )


def test_apply_geographic_prior_rejects_non_2d_logits() -> None:
    conditioner = LogitConditioner(gamma=1.0, epsilon=0.01, top_k=3)

    with pytest.raises(ValueError, match="2D"):
        conditioner.apply_geographic_prior(
            classifier_output=make_classifier_output(torch.tensor([1.0, 2.0, 3.0])),
            prior_mask=make_prior_mask([1.0, 1.0, 1.0]),
        )


def test_apply_geographic_prior_rejects_non_1d_prior_mask() -> None:
    conditioner = LogitConditioner(gamma=1.0, epsilon=0.01, top_k=3)

    with pytest.raises(ValueError, match="1D"):
        conditioner.apply_geographic_prior(
            classifier_output=make_classifier_output(torch.tensor([[1.0, 2.0, 3.0]])),
            prior_mask=PriorMask(
                values=torch.tensor([[1.0, 1.0, 1.0]]),
                class_index_id="stub",
            ),
        )


def test_apply_geographic_prior_rejects_prior_length_mismatch() -> None:
    conditioner = LogitConditioner(gamma=1.0, epsilon=0.01, top_k=3)

    with pytest.raises(ValueError, match="class count"):
        conditioner.apply_geographic_prior(
            classifier_output=make_classifier_output(torch.tensor([[1.0, 2.0, 3.0]])),
            prior_mask=make_prior_mask([1.0, 1.0]),
        )


def test_apply_geographic_prior_returns_empty_list_for_empty_crop_batch() -> None:
    conditioner = LogitConditioner(gamma=1.0, epsilon=0.01, top_k=3)

    predictions = conditioner.apply_geographic_prior(
        classifier_output=make_classifier_output(torch.empty((0, 3))),
        prior_mask=make_prior_mask([1.0, 1.0, 1.0]),
    )

    assert predictions == []


def test_apply_geographic_prior_returns_top_k_predictions_per_crop() -> None:
    conditioner = LogitConditioner(gamma=1.0, epsilon=0.01, top_k=2)
    logits = torch.tensor(
        [
            [0.0, 2.0, 1.0],
            [3.0, 0.0, 1.0],
        ]
    )

    predictions = conditioner.apply_geographic_prior(
        classifier_output=make_classifier_output(logits),
        prior_mask=make_prior_mask([1.0, 0.01, 1.0]),
    )
    expected_probabilities = torch.softmax(
        logits + torch.log(torch.tensor([1.0, 0.01, 1.0])),
        dim=-1,
    )

    assert [[prediction.class_id for prediction in crop] for crop in predictions] == [
        [2, 0],
        [0, 2],
    ]
    assert len(predictions) == 2
    assert all(len(crop) == 2 for crop in predictions)
    assert predictions[0][0].confidence == pytest.approx(
        float(expected_probabilities[0, 2])
    )


def test_apply_geographic_prior_clamps_top_k_to_class_count() -> None:
    conditioner = LogitConditioner(gamma=1.0, epsilon=0.01, top_k=12)

    predictions = conditioner.apply_geographic_prior(
        classifier_output=make_classifier_output(torch.tensor([[1.0, 2.0, 3.0]])),
        prior_mask=make_prior_mask([1.0, 1.0, 1.0]),
    )

    assert len(predictions) == 1
    assert len(predictions[0]) == 3


def test_apply_geographic_prior_with_gamma_zero_matches_raw_softmax() -> None:
    conditioner = LogitConditioner(gamma=0.0, epsilon=0.01, top_k=3)
    logits = torch.tensor([[0.0, 2.0, 1.0]])

    predictions = conditioner.apply_geographic_prior(
        classifier_output=make_classifier_output(logits),
        prior_mask=make_prior_mask([1.0, 0.01, 1.0]),
    )

    expected_probabilities = torch.softmax(logits, dim=-1)

    assert [prediction.class_id for prediction in predictions[0]] == [1, 2, 0]
    assert predictions[0][0].confidence == pytest.approx(
        float(expected_probabilities[0, 1])
    )


def make_class_index() -> ClassIndex:
    return ClassIndex(
        id="stub",
        taxon_id_by_class_id={
            0: 101,
            1: 202,
            2: 303,
        },
    )


def make_classifier_output(logits: torch.Tensor) -> RawClassifierOutput:
    return RawClassifierOutput(logits=logits, class_index=make_class_index())


def make_prior_mask(values: list[float]) -> PriorMask:
    return PriorMask(
        values=torch.tensor(values, dtype=torch.float32),
        class_index_id="stub",
    )

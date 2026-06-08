import torch

from wild_catalog.classifier.types import ClassPrediction, RawClassifierOutput
from wild_catalog.prior.types import PriorMask


class LogitConditioner:
    def __init__(self, gamma: float, epsilon: float, top_k: int) -> None:
        if gamma < 0:
            raise ValueError("gamma must be greater than or equal to 0.")

        if epsilon <= 0:
            raise ValueError("epsilon must be greater than 0.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0.")

        self._gamma = gamma
        self._epsilon = epsilon
        self._top_k = top_k

    def apply_geographic_prior(
        self,
        classifier_output: RawClassifierOutput,
        prior_mask: PriorMask,
    ) -> list[list[ClassPrediction]]:
        logits = classifier_output.logits

        if classifier_output.class_index.id != prior_mask.class_index_id:
            raise ValueError("Prior mask class index does not match classifier output.")

        if logits.ndim != 2:
            raise ValueError("Classifier logits must be a 2D tensor.")

        if prior_mask.values.ndim != 1:
            raise ValueError("Prior mask values must be a 1D tensor.")

        if logits.shape[1] != prior_mask.values.shape[0]:
            raise ValueError("Prior mask length must match classifier output class count.")

        if logits.shape[0] == 0:
            return []

        top_k = min(self._top_k, logits.shape[1])
        prior_values = prior_mask.values.to(device=logits.device, dtype=logits.dtype)

        safe_prior = torch.clamp(prior_values, min=self._epsilon)
        conditioned_logits = logits + self._gamma * torch.log(safe_prior)
        probabilities = torch.softmax(conditioned_logits, dim=-1)

        top_probabilities, top_indices = torch.topk(probabilities, k=top_k, dim=-1)

        results: list[list[ClassPrediction]] = []

        for crop_probabilities, crop_indices in zip(
            top_probabilities,
            top_indices,
            strict=True,
        ):
            crop_predictions = [
                ClassPrediction(
                    class_id=int(class_id),
                    confidence=float(confidence),
                )
                for confidence, class_id in zip(
                    crop_probabilities.detach().cpu(),
                    crop_indices.detach().cpu(),
                    strict=True,
                )
            ]
            results.append(crop_predictions)

        return results

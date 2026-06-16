import torch

from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.range_data.prior_mask import PriorMask
from wild_catalog.species_classifier.raw_classifier_output import RawClassifierOutput


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
    ) -> list[list[Prediction]]:
        probabilities = classifier_output.probabilities

        if classifier_output.class_index.id != prior_mask.class_index_id:
            raise ValueError("Prior mask class index does not match classifier output.")

        if probabilities.ndim != 2:
            raise ValueError("Classifier probabilities must be a 2D tensor.")

        if prior_mask.values.ndim != 1:
            raise ValueError("Prior mask values must be a 1D tensor.")

        if probabilities.shape[1] != prior_mask.values.shape[0]:
            raise ValueError("Prior mask length must match classifier output class count.")

        if probabilities.shape[0] == 0:
            return []

        top_k = min(self._top_k, probabilities.shape[1])
        prior_values = prior_mask.values.to(
            device=probabilities.device,
            dtype=probabilities.dtype,
        )

        safe_probabilities = torch.clamp(probabilities, min=self._epsilon)
        safe_prior = torch.clamp(prior_values, min=self._epsilon)
        conditioned_logits = torch.log(safe_probabilities) + self._gamma * torch.log(
            safe_prior,
        )
        conditioned_probabilities = torch.softmax(conditioned_logits, dim=-1)

        top_probabilities, top_indices = torch.topk(
            conditioned_probabilities,
            k=top_k,
            dim=-1,
        )

        results: list[list[Prediction]] = []

        for crop_probabilities, crop_indices in zip(
            top_probabilities,
            top_indices,
            strict=True,
        ):
            crop_predictions = [
                Prediction(
                    class_id=int(class_id),
                    confidence=float(confidence),
                    is_present=self._is_present(prior_mask, int(class_id)),
                    taxonomy=self._taxonomy_for_class(
                        classifier_output,
                        int(class_id),
                    ),
                    taxonomy_common_names=self._taxonomy_for_class(
                        classifier_output,
                        int(class_id),
                    ),
                    taxon_id=classifier_output.class_index.taxon_id_by_class_id.get(
                        int(class_id),
                        -1,
                    ),
                )
                for confidence, class_id in zip(
                    crop_probabilities.detach().cpu(),
                    crop_indices.detach().cpu(),
                    strict=True,
                )
            ]
            results.append(crop_predictions)

        return results

    @staticmethod
    def _is_present(prior_mask: PriorMask, class_id: int) -> bool:
        return bool(prior_mask.values[class_id].detach().cpu() >= 1.0)

    @staticmethod
    def _taxonomy_for_class(
        classifier_output: RawClassifierOutput,
        class_id: int,
    ) -> tuple[str, ...]:
        taxonomy_path = classifier_output.class_index.taxonomy_path_by_class_id.get(
            class_id,
        )
        if taxonomy_path:
            return taxonomy_path

        label = classifier_output.label_by_class_id.get(class_id)
        if label:
            return (label,)

        return (str(class_id),)

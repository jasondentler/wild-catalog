from dataclasses import replace

from wild_catalog.core.taxonomy_name_normalization import (
    capitalize_words,
    normalize_scientific_names,
)
from wild_catalog.identify_pipeline.prediction import Prediction


class PredictionNameNormalizer:
    def normalize_predictions(
        self,
        predictions: tuple[Prediction, ...],
    ) -> tuple[Prediction, ...]:
        return tuple(self.normalize_prediction(prediction) for prediction in predictions)

    def normalize_prediction(self, prediction: Prediction) -> Prediction:
        return replace(
            prediction,
            taxonomy=normalize_scientific_names(
                prediction.taxonomy,
                prediction.taxonomy_rank_names,
            ),
            taxonomy_common_names=tuple(
                capitalize_words(name) for name in prediction.taxonomy_common_names
            ),
        )

import re
from dataclasses import replace

from wild_catalog.identify_pipeline.prediction import Prediction

_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)
_SPECIES_AND_BELOW_RANKS = {"species", "subspecies", "variety", "form"}


class PredictionNameNormalizer:
    def normalize_predictions(
        self,
        predictions: tuple[Prediction, ...],
    ) -> tuple[Prediction, ...]:
        return tuple(self.normalize_prediction(prediction) for prediction in predictions)

    def normalize_prediction(self, prediction: Prediction) -> Prediction:
        return replace(
            prediction,
            taxonomy=_normalize_scientific_names(
                prediction.taxonomy,
                prediction.taxonomy_rank_names,
            ),
            taxonomy_common_names=tuple(
                _capitalize_words(name) for name in prediction.taxonomy_common_names
            ),
        )


def _normalize_scientific_names(
    names: tuple[str, ...],
    ranks: tuple[str, ...],
) -> tuple[str, ...]:
    normalized_names = []
    species_or_below = False

    for name, rank_name in zip(names, ranks, strict=True):
        rank = rank_name.lower()
        species_or_below = species_or_below or rank in _SPECIES_AND_BELOW_RANKS
        if species_or_below:
            normalized_names.append(name.lower())
        else:
            normalized_names.append(_capitalize_words(name))

    return tuple(normalized_names)


def _capitalize_words(name: str) -> str:
    return _WORD_RE.sub(
        lambda match: match.group(0)[:1].upper() + match.group(0)[1:].lower(),
        name,
    )

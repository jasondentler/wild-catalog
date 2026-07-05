import re

_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)
_SPECIES_AND_BELOW_RANKS = {"species", "subspecies", "variety", "form"}


def normalize_scientific_names(
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
            normalized_names.append(capitalize_words(name))

    return tuple(normalized_names)


def capitalize_words(name: str) -> str:
    return _WORD_RE.sub(
        lambda match: match.group(0)[:1].upper() + match.group(0)[1:].lower(),
        name,
    )

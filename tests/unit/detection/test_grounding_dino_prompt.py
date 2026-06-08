from wild_catalog.core.config import Settings
from wild_catalog.detection.grounding_dino_prompt import DEFAULT_GROUNDING_DINO_PROMPT


def test_default_grounding_dino_prompt_contains_only_organism_groups() -> None:
    assert "bird" in DEFAULT_GROUNDING_DINO_PROMPT
    assert "mushroom" in DEFAULT_GROUNDING_DINO_PROMPT
    assert "car" not in DEFAULT_GROUNDING_DINO_PROMPT
    assert "Nannopterum" not in DEFAULT_GROUNDING_DINO_PROMPT


def test_settings_use_default_grounding_dino_prompt() -> None:
    assert Settings().grounding_dino_prompt == DEFAULT_GROUNDING_DINO_PROMPT

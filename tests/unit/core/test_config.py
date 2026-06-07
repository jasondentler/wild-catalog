from wild_catalog.core.config import Settings


def test_settings_defaults_to_development() -> None:
    assert Settings().env == "development"

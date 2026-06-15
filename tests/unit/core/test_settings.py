from wild_catalog.core.settings import Settings


def test_settings_from_env_uses_environment_overrides(
    monkeypatch,
) -> None:
    monkeypatch.setenv("WILD_CATALOG_MAX_UPLOAD_BYTES", "12345")
    monkeypatch.setenv("WILD_CATALOG_MAX_IMAGE_PIXELS", "67890")
    monkeypatch.setenv("WILD_CATALOG_CROP_MARGIN_RATIO", "0.25")
    monkeypatch.setenv("WILD_CATALOG_CROP_MARGIN_MIN_PX", "12")

    settings = Settings.from_env()

    assert settings.max_upload_bytes == 12345
    assert settings.max_image_pixels == 67890
    assert settings.crop_margin_ratio == 0.25
    assert settings.crop_margin_min_px == 12


def test_settings_from_env_uses_defaults_when_env_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.delenv("WILD_CATALOG_MAX_UPLOAD_BYTES", raising=False)
    monkeypatch.delenv("WILD_CATALOG_MAX_IMAGE_PIXELS", raising=False)
    monkeypatch.delenv("WILD_CATALOG_CROP_MARGIN_RATIO", raising=False)
    monkeypatch.delenv("WILD_CATALOG_CROP_MARGIN_MIN_PX", raising=False)

    settings = Settings.from_env()

    assert settings.max_upload_bytes == 100_000_000
    assert settings.max_image_pixels == 11_648 * 8_742
    assert settings.crop_margin_ratio == 0.10
    assert settings.crop_margin_min_px == 8

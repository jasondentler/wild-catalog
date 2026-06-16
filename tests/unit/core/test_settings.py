from wild_catalog.core.settings import Settings


def test_settings_from_env_uses_environment_overrides(
    monkeypatch,
) -> None:
    monkeypatch.setenv("WILD_CATALOG_MAX_UPLOAD_BYTES", "12345")
    monkeypatch.setenv("WILD_CATALOG_MAX_IMAGE_PIXELS", "67890")
    monkeypatch.setenv("WILD_CATALOG_CROP_MARGIN_RATIO", "0.25")
    monkeypatch.setenv("WILD_CATALOG_CROP_MARGIN_MIN_PX", "12")
    monkeypatch.setenv("WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K", "7")
    monkeypatch.setenv("WILD_CATALOG_RANGE_PRIOR_EPSILON", "0.03")
    monkeypatch.setenv("WILD_CATALOG_RANGE_PRIOR_CACHE_ENABLED", "false")
    monkeypatch.setenv("WILD_CATALOG_RANGE_PRIOR_CACHE_MAX_ENTRIES", "123")
    monkeypatch.setenv("WILD_CATALOG_RANGE_PRIOR_CACHE_H3_RESOLUTION", "8")
    monkeypatch.setenv("WILD_CATALOG_LOGIT_CONDITIONING_GAMMA", "3.5")
    monkeypatch.setenv("WILD_CATALOG_LOGIT_CONDITIONING_EPSILON", "0.000001")
    monkeypatch.setenv(
        "WILD_CATALOG_RANGE_STORE_DATABASE_PATH",
        "custom/range-store.sqlite",
    )
    monkeypatch.setenv(
        "WILD_CATALOG_RANGE_GEOPACKAGE_DOWNLOAD_DIR",
        "custom/geopackages",
    )

    settings = Settings.from_env()

    assert settings.max_upload_bytes == 12345
    assert settings.max_image_pixels == 67890
    assert settings.crop_margin_ratio == 0.25
    assert settings.crop_margin_min_px == 12
    assert settings.species_classifier_top_k == 7
    assert settings.prior_epsilon == 0.03
    assert settings.range_prior_cache_enabled is False
    assert settings.range_prior_cache_max_entries == 123
    assert settings.range_prior_cache_h3_resolution == 8
    assert settings.logit_conditioning_gamma == 3.5
    assert settings.logit_conditioning_epsilon == 0.000001
    assert str(settings.range_store_database_path) == "custom/range-store.sqlite"
    assert str(settings.range_geopackage_download_dir) == "custom/geopackages"


def test_settings_from_env_uses_defaults_when_env_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.delenv("WILD_CATALOG_MAX_UPLOAD_BYTES", raising=False)
    monkeypatch.delenv("WILD_CATALOG_MAX_IMAGE_PIXELS", raising=False)
    monkeypatch.delenv("WILD_CATALOG_CROP_MARGIN_RATIO", raising=False)
    monkeypatch.delenv("WILD_CATALOG_CROP_MARGIN_MIN_PX", raising=False)
    monkeypatch.delenv("WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K", raising=False)
    monkeypatch.delenv("WILD_CATALOG_RANGE_PRIOR_EPSILON", raising=False)
    monkeypatch.delenv("WILD_CATALOG_RANGE_PRIOR_CACHE_ENABLED", raising=False)
    monkeypatch.delenv("WILD_CATALOG_RANGE_PRIOR_CACHE_MAX_ENTRIES", raising=False)
    monkeypatch.delenv("WILD_CATALOG_RANGE_PRIOR_CACHE_H3_RESOLUTION", raising=False)
    monkeypatch.delenv("WILD_CATALOG_LOGIT_CONDITIONING_GAMMA", raising=False)
    monkeypatch.delenv("WILD_CATALOG_LOGIT_CONDITIONING_EPSILON", raising=False)
    monkeypatch.delenv("WILD_CATALOG_RANGE_STORE_DATABASE_PATH", raising=False)
    monkeypatch.delenv("WILD_CATALOG_RANGE_GEOPACKAGE_DOWNLOAD_DIR", raising=False)

    settings = Settings.from_env()

    assert settings.max_upload_bytes == 100_000_000
    assert settings.max_image_pixels == 11_648 * 8_742
    assert settings.crop_margin_ratio == 0.10
    assert settings.crop_margin_min_px == 8
    assert settings.species_classifier_top_k == 20
    assert settings.prior_epsilon == 0.01
    assert settings.range_prior_cache_enabled is True
    assert settings.range_prior_cache_max_entries == 10_000
    assert settings.range_prior_cache_h3_resolution == 7
    assert settings.logit_conditioning_gamma == 2.0
    assert settings.logit_conditioning_epsilon == 1e-12
    assert str(settings.range_store_database_path) == (
        "data/range-data/inaturalist-open-range-store.sqlite"
    )
    assert str(settings.range_geopackage_download_dir) == "data/range-data/geopackages"

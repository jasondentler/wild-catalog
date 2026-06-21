from types import SimpleNamespace

from wild_catalog.api.dependencies import get_identify_pipeline, get_settings


def test_get_settings_is_cached(monkeypatch) -> None:
    calls = []

    class _Settings:
        @classmethod
        def from_env(cls):
            calls.append("called")
            return SimpleNamespace(marker="settings")

    monkeypatch.setattr("wild_catalog.api.dependencies.Settings", _Settings)
    get_settings.cache_clear()

    try:
        first = get_settings()
        second = get_settings()

        assert first.marker == "settings"
        assert second is first
        assert calls == ["called"]
    finally:
        get_settings.cache_clear()


def test_get_identify_pipeline_builds_pipeline(monkeypatch) -> None:
    settings = SimpleNamespace(
        marker="settings",
        logit_conditioning_gamma=2.0,
        logit_conditioning_epsilon=1e-12,
        species_classifier_top_k=5,
        range_store_database_path="range.sqlite",
        taxonomy_store_database_path="taxonomy.sqlite",
    )
    conversion = SimpleNamespace(marker="conversion")
    wildlife_detector = SimpleNamespace(marker="wildlife_detector", device="mps")
    detection_deduplicator = SimpleNamespace(marker="detection_deduplicator")
    image_cropper = SimpleNamespace(marker="image_cropper")
    species_classifier = SimpleNamespace(marker="species_classifier")
    expected_range_prior_service = SimpleNamespace(marker="range_prior_service")
    expected_logit_conditioner = SimpleNamespace(marker="logit_conditioner")
    expected_range_store = SimpleNamespace(marker="range_store")
    expected_taxonomy_store = SimpleNamespace(
        marker="taxonomy_store",
        get_taxon_ids_by_scientific_names=object(),
    )
    expected_taxon_lookup = SimpleNamespace(marker="taxon_lookup")
    expected_taxonomy_service = SimpleNamespace(marker="taxonomy_service")
    expected_name_normalizer = SimpleNamespace(marker="name_normalizer")
    detection_processing_pipeline = SimpleNamespace(
        marker="detection_processing_pipeline"
    )

    monkeypatch.setattr("wild_catalog.api.dependencies.get_settings", lambda: settings)
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.ImageConversionService",
        lambda received_settings: conversion if received_settings is settings else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.WildlifeDetector",
        lambda: wildlife_detector,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.DetectionDeduplicator",
        lambda: detection_deduplicator,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.ImageCropper",
        lambda received_settings: image_cropper if received_settings is settings else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.SQLiteSpeciesRangeStore",
        lambda database_path: expected_range_store
        if database_path == "range.sqlite"
        else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.SQLiteTaxonomyStore",
        lambda database_path: expected_taxonomy_store
        if database_path == "taxonomy.sqlite"
        else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.local_then_inaturalist_taxon_lookup",
        lambda local_lookup: expected_taxon_lookup
        if local_lookup is expected_taxonomy_store.get_taxon_ids_by_scientific_names
        else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.SpeciesClassifier",
        lambda received_settings, *, device, taxon_id_by_scientific_name: species_classifier
        if (
            received_settings is settings
            and device == "mps"
            and taxon_id_by_scientific_name is expected_taxon_lookup
        )
        else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.SpeciesRangePriorService",
        lambda received_settings, *, store: expected_range_prior_service
        if received_settings is settings and store is expected_range_store
        else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.TaxonomyService",
        lambda store: expected_taxonomy_service
        if store is expected_taxonomy_store
        else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.PredictionNameNormalizer",
        lambda: expected_name_normalizer,
    )

    def build_logit_conditioner(*, gamma, epsilon, top_k):
        if gamma == 2.0 and epsilon == 1e-12 and top_k == 5:
            return expected_logit_conditioner
        return None

    monkeypatch.setattr(
        "wild_catalog.api.dependencies.LogitConditioner",
        build_logit_conditioner,
    )

    def build_detection_processing_pipeline(
        received_cropper,
        received_classifier,
        *,
        range_prior_service: object,
        logit_conditioner: object,
        taxonomy_service: object,
        name_normalizer: object,
    ):
        if (
            received_cropper is image_cropper
            and received_classifier is species_classifier
            and range_prior_service is expected_range_prior_service
            and logit_conditioner is expected_logit_conditioner
            and taxonomy_service is expected_taxonomy_service
            and name_normalizer is expected_name_normalizer
        ):
            return detection_processing_pipeline
        return None

    monkeypatch.setattr(
        "wild_catalog.api.dependencies.DetectionProcessingPipeline",
        build_detection_processing_pipeline,
    )

    get_identify_pipeline.cache_clear()

    try:
        pipeline = get_identify_pipeline()

        assert pipeline._settings is settings
        assert pipeline._conversion is conversion
        assert pipeline._wildlife_detector is wildlife_detector
        assert pipeline._detection_deduplicator is detection_deduplicator
        assert pipeline._detection_processing_pipeline is detection_processing_pipeline
    finally:
        get_identify_pipeline.cache_clear()

from types import SimpleNamespace

from wild_catalog.preop import cli as preop_cli
from wild_catalog.range_data import preop as range_preop
from wild_catalog.species_classifier import preop as classifier_preop
from wild_catalog.taxonomy import preop as taxonomy_preop
from wild_catalog.wildlife_detection import preop as detector_preop


def test_taxonomy_preop_imports_taxonomy_archive(monkeypatch) -> None:
    settings = SimpleNamespace(
        taxonomy_store_database_path="taxonomy.sqlite",
        taxonomy_archive_download_dir="taxonomy-downloads",
        taxonomy_languages=("en-US", "es-MX"),
    )
    calls = []

    monkeypatch.setattr(taxonomy_preop.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(
        taxonomy_preop,
        "import_taxonomy_archive_if_missing",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    taxonomy_preop.main()

    assert calls == [
        (
            ("taxonomy.sqlite", "taxonomy-downloads"),
            {"languages": ("en-US", "es-MX")},
        )
    ]


def test_range_preop_imports_range_maps(monkeypatch) -> None:
    settings = SimpleNamespace(
        range_store_database_path="range.sqlite",
        range_geopackage_download_dir="geopackages",
    )
    calls = []

    monkeypatch.setattr(range_preop.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(
        range_preop,
        "import_inaturalist_open_range_data_if_missing",
        lambda *args: calls.append(args),
    )

    range_preop.main()

    assert calls == [("range.sqlite", "geopackages")]


def test_classifier_preop_loads_classifier_model(monkeypatch) -> None:
    settings = SimpleNamespace(marker="settings")
    calls = []

    monkeypatch.setattr(classifier_preop.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(
        classifier_preop,
        "SpeciesClassifier",
        lambda received_settings: calls.append(received_settings),
    )

    classifier_preop.main()

    assert calls == [settings]


def test_detector_preop_loads_detector_model(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(detector_preop, "WildlifeDetector", lambda: calls.append("loaded"))

    detector_preop.main()

    assert calls == ["loaded"]


def test_aggregate_preop_runs_steps_in_order(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(preop_cli, "import_taxonomy_dwca", lambda: calls.append("taxonomy"))
    monkeypatch.setattr(preop_cli, "import_range_maps", lambda: calls.append("range"))
    monkeypatch.setattr(preop_cli, "prepare_classifier_model", lambda: calls.append("classifier"))
    monkeypatch.setattr(preop_cli, "prepare_detector_model", lambda: calls.append("detector"))

    preop_cli.main()

    assert calls == ["taxonomy", "range", "classifier", "detector"]

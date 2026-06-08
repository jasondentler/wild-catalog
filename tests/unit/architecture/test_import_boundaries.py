from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src" / "wild_catalog"


def read_python_files(package: str) -> list[Path]:
    package_root = SRC_ROOT / package
    return list(package_root.rglob("*.py"))


def test_core_does_not_import_feature_packages() -> None:
    forbidden_imports = [
        "wild_catalog.api",
        "wild_catalog.pipeline",
        "wild_catalog.conversion",
        "wild_catalog.detection",
        "wild_catalog.deduplication",
        "wild_catalog.cropping",
        "wild_catalog.classifier",
        "wild_catalog.prior",
        "wild_catalog.conditioning",
        "wild_catalog.taxonomy",
    ]

    for path in read_python_files("core"):
        text = path.read_text()

        for forbidden_import in forbidden_imports:
            assert forbidden_import not in text, f"{path} must not import {forbidden_import}"


def test_services_do_not_import_api_models() -> None:
    service_packages = [
        "conversion",
        "detection",
        "deduplication",
        "cropping",
        "classifier",
        "prior",
        "conditioning",
        "taxonomy",
        "pipeline",
    ]

    forbidden_imports = [
        "wild_catalog.api.request_models",
        "wild_catalog.api.response_models",
        "wild_catalog.api.content_negotiation",
        "wild_catalog.api.multipart",
        "fastapi.responses",
    ]

    for package in service_packages:
        for path in read_python_files(package):
            text = path.read_text()

            for forbidden_import in forbidden_imports:
                assert forbidden_import not in text, f"{path} must not import {forbidden_import}"


def test_pipeline_does_not_import_concrete_classifier_plugins() -> None:
    forbidden_imports = [
        "wild_catalog.classifier.birder",
        "BirderSpeciesClassifier",
    ]

    for path in read_python_files("pipeline"):
        text = path.read_text()

        for forbidden_import in forbidden_imports:
            assert forbidden_import not in text, f"{path} must not import {forbidden_import}"


def test_prior_import_boundaries() -> None:
    forbidden_imports = [
        "wild_catalog.api",
        "wild_catalog.taxonomy",
        "wild_catalog.pipeline",
        "wild_catalog.classifier.birder",
        "BirderSpeciesClassifier",
    ]

    for path in read_python_files("prior"):
        text = path.read_text()

        for forbidden_import in forbidden_imports:
            assert forbidden_import not in text, f"{path} must not import {forbidden_import}"


def test_taxonomy_import_boundaries() -> None:
    forbidden_imports = [
        "wild_catalog.api",
        "wild_catalog.detection",
        "wild_catalog.cropping",
        "wild_catalog.prior.store",
        "wild_catalog.conditioning",
        "wild_catalog.pipeline",
        "wild_catalog.classifier.birder",
        "BirderSpeciesClassifier",
    ]

    for path in read_python_files("taxonomy"):
        text = path.read_text()

        for forbidden_import in forbidden_imports:
            assert forbidden_import not in text, f"{path} must not import {forbidden_import}"

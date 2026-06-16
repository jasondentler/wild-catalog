import os
from dataclasses import dataclass
from pathlib import Path

MDV6_APACHE_RTDETR_E_URL = (
    "https://zenodo.org/records/15398270/files/"
    "MDV6-apa-rtdetr-e.pth?download=1"
)

MDV6_APACHE_RTDETR_C_URL = (
    "https://zenodo.org/records/15398270/files/"
    "MDV6-apa-rtdetr-c.pth?download=1"
)


DEFAULTS = {
    "WILD_CATALOG_MAX_UPLOAD_BYTES": 100_000_000,
    "WILD_CATALOG_MAX_IMAGE_PIXELS": 11_648 * 8_742,
    "WILD_CATALOG_CROP_MARGIN_RATIO": 0.10,
    "WILD_CATALOG_CROP_MARGIN_MIN_PX": 8,
    "WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K": 20,
    "WILD_CATALOG_RANGE_STORE_DATABASE_PATH": Path(
        "data/range-data/inaturalist-open-range-store.sqlite"
    ),
    "WILD_CATALOG_RANGE_GEOPACKAGE_DOWNLOAD_DIR": Path(
        "data/range-data/geopackages"
    ),
}


@dataclass(frozen=True, slots=True)
class Settings:
    max_upload_bytes: int = DEFAULTS["WILD_CATALOG_MAX_UPLOAD_BYTES"]
    max_image_pixels: int = DEFAULTS["WILD_CATALOG_MAX_IMAGE_PIXELS"]
    crop_margin_ratio: float = DEFAULTS["WILD_CATALOG_CROP_MARGIN_RATIO"]
    crop_margin_min_px: int = DEFAULTS["WILD_CATALOG_CROP_MARGIN_MIN_PX"]
    species_classifier_top_k: int = DEFAULTS["WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K"]
    range_store_database_path: Path = DEFAULTS[
        "WILD_CATALOG_RANGE_STORE_DATABASE_PATH"
    ]
    range_geopackage_download_dir: Path = DEFAULTS[
        "WILD_CATALOG_RANGE_GEOPACKAGE_DOWNLOAD_DIR"
    ]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            max_upload_bytes=cls._get_int_value("WILD_CATALOG_MAX_UPLOAD_BYTES"),
            max_image_pixels=cls._get_int_value("WILD_CATALOG_MAX_IMAGE_PIXELS"),
            crop_margin_ratio=cls._get_float_value("WILD_CATALOG_CROP_MARGIN_RATIO"),
            crop_margin_min_px=cls._get_int_value("WILD_CATALOG_CROP_MARGIN_MIN_PX"),
            species_classifier_top_k=cls._get_int_value(
                "WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K"
            ),
            range_store_database_path=cls._get_path_value(
                "WILD_CATALOG_RANGE_STORE_DATABASE_PATH"
            ),
            range_geopackage_download_dir=cls._get_path_value(
                "WILD_CATALOG_RANGE_GEOPACKAGE_DOWNLOAD_DIR"
            ),
        )

    @staticmethod
    def _get_str_value(key: str) -> str:
        default = DEFAULTS[key]
        return os.getenv(key, str(default))

    @staticmethod
    def _get_int_value(key: str) -> int:
        return int(Settings._get_str_value(key))

    @staticmethod
    def _get_float_value(key: str) -> float:
        return float(Settings._get_str_value(key))

    @staticmethod
    def _get_path_value(key: str) -> Path:
        return Path(Settings._get_str_value(key))

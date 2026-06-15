import os
from dataclasses import dataclass

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
}


@dataclass(frozen=True, slots=True)
class Settings:
    max_upload_bytes: int = DEFAULTS["WILD_CATALOG_MAX_UPLOAD_BYTES"]
    max_image_pixels: int = DEFAULTS["WILD_CATALOG_MAX_IMAGE_PIXELS"]
    crop_margin_ratio: float = DEFAULTS["WILD_CATALOG_CROP_MARGIN_RATIO"]
    crop_margin_min_px: int = DEFAULTS["WILD_CATALOG_CROP_MARGIN_MIN_PX"]
    species_classifier_top_k: int = DEFAULTS["WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K"]

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
        )

    @staticmethod
    def _get_str_value(key: str) -> str:
        default = DEFAULTS[key]
        return os.getenv(key, default)

    @staticmethod
    def _get_int_value(key: str) -> int:
        return int(Settings._get_str_value(key))

    @staticmethod
    def _get_float_value(key: str) -> float:
        return float(Settings._get_str_value(key))

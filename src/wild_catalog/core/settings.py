import os
from dataclasses import dataclass

DEFAULTS = {
    "WILD_CATALOG_MAX_UPLOAD_BYTES": 100_000_000,
    "WILD_CATALOG_MAX_IMAGE_PIXELS": 11_648 * 8_742,
}


@dataclass(frozen=True, slots=True)
class Settings:
    max_upload_bytes: int = DEFAULTS["WILD_CATALOG_MAX_UPLOAD_BYTES"]
    max_image_pixels: int = DEFAULTS["WILD_CATALOG_MAX_IMAGE_PIXELS"]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            max_upload_bytes=cls._get_int_value("WILD_CATALOG_MAX_UPLOAD_BYTES"),
            max_image_pixels=cls._get_int_value("WILD_CATALOG_MAX_IMAGE_PIXELS"),
        )

    @staticmethod
    def _get_str_value(key: str) -> str:
        default = DEFAULTS[key]
        return os.getenv(key, default)

    @staticmethod
    def _get_int_value(key: str) -> int:
        return int(Settings._get_str_value(key))

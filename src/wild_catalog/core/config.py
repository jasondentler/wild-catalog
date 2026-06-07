import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    env: str = "development"
    max_upload_bytes: int = 26_214_400
    max_image_pixels: int = 24_000_000
    max_detections: int = 8
    crop_margin_ratio: float = 0.12
    detector_backend: str = "stub"
    classifier_backend: str = "stub"
    preload_models: bool = False
    max_concurrent_identify_requests: int = 1
    enable_platform_image_conversion: bool = True
    platform_image_converter: str = "auto"
    platform_conversion_timeout_seconds: int = 10
    grounding_dino_model_id: str = "IDEA-Research/grounding-dino-tiny"
    grounding_dino_prompt: str = (
        "bird . mammal . animal . reptile . amphibian . fish . "
        "insect . butterfly . moth . beetle . dragonfly . spider . snail . "
        "flower . plant . tree . leaf . grass . moss . lichen . "
        "mushroom . fungus ."
    )
    grounding_dino_box_threshold: float = 0.25
    grounding_dino_text_threshold: float = 0.25
    classifier_batch_size: int = 8
    classifier_top_k: int = 12
    classifier_model_cache_path: Path | None = None
    range_map_store_path: Path | None = None
    prior_epsilon: float = 0.01
    prior_gamma: float = 1.0
    taxonomy_dwca_url: str = "https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip"
    taxonomy_dwca_path: Path | None = None
    taxonomy_store_path: Path = Path("data/taxonomy")
    taxonomy_default_language: str = "en-US"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            env=os.getenv("WILD_CATALOG_ENV", "development"),
            max_upload_bytes=int(os.getenv("WILD_CATALOG_MAX_UPLOAD_BYTES", "26214400")),
            max_image_pixels=int(os.getenv("WILD_CATALOG_MAX_IMAGE_PIXELS", "24000000")),
            max_detections=int(os.getenv("WILD_CATALOG_MAX_DETECTIONS", "8")),
            crop_margin_ratio=float(os.getenv("WILD_CATALOG_CROP_MARGIN_RATIO", "0.12")),
            detector_backend=os.getenv("WILD_CATALOG_DETECTOR_BACKEND", "stub"),
            classifier_backend=os.getenv("WILD_CATALOG_CLASSIFIER_BACKEND", "stub"),
            preload_models=_read_bool("WILD_CATALOG_PRELOAD_MODELS", False),
            max_concurrent_identify_requests=int(
                os.getenv("WILD_CATALOG_MAX_CONCURRENT_IDENTIFY_REQUESTS", "1")
            ),
            enable_platform_image_conversion=_read_bool(
                "WILD_CATALOG_ENABLE_PLATFORM_IMAGE_CONVERSION",
                True,
            ),
            platform_image_converter=os.getenv(
                "WILD_CATALOG_PLATFORM_IMAGE_CONVERTER",
                "auto",
            ),
            platform_conversion_timeout_seconds=int(
                os.getenv("WILD_CATALOG_PLATFORM_CONVERSION_TIMEOUT_SECONDS", "10")
            ),
            grounding_dino_model_id=os.getenv(
                "WILD_CATALOG_GROUNDING_DINO_MODEL_ID",
                "IDEA-Research/grounding-dino-tiny",
            ),
            grounding_dino_prompt=os.getenv(
                "WILD_CATALOG_GROUNDING_DINO_PROMPT",
                cls.grounding_dino_prompt,
            ),
            grounding_dino_box_threshold=float(
                os.getenv("WILD_CATALOG_GROUNDING_DINO_BOX_THRESHOLD", "0.25")
            ),
            grounding_dino_text_threshold=float(
                os.getenv("WILD_CATALOG_GROUNDING_DINO_TEXT_THRESHOLD", "0.25")
            ),
            classifier_batch_size=int(
                os.getenv("WILD_CATALOG_SPECIES_CLASSIFIER_BATCH_SIZE", "8")
            ),
            classifier_top_k=int(os.getenv("WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K", "12")),
            classifier_model_cache_path=_read_optional_path(
                "WILD_CATALOG_SPECIES_CLASSIFIER_MODEL_CACHE_PATH"
            ),
            range_map_store_path=_read_optional_path("WILD_CATALOG_RANGE_MAP_STORE_PATH"),
            prior_epsilon=float(os.getenv("WILD_CATALOG_PRIOR_EPSILON", "0.01")),
            prior_gamma=float(os.getenv("WILD_CATALOG_PRIOR_GAMMA", "1.0")),
            taxonomy_dwca_url=os.getenv(
                "WILD_CATALOG_TAXONOMY_DWCA_URL",
                "https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip",
            ),
            taxonomy_dwca_path=_read_optional_path("WILD_CATALOG_TAXONOMY_DWCA_PATH"),
            taxonomy_store_path=Path(
                os.getenv("WILD_CATALOG_TAXONOMY_STORE_PATH", "data/taxonomy")
            ),
            taxonomy_default_language=os.getenv(
                "WILD_CATALOG_TAXONOMY_DEFAULT_LANGUAGE",
                "en-US",
            ),
        )


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_optional_path(name: str) -> Path | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return None

    return Path(value)

from dataclasses import replace

from PIL import Image

from wild_catalog.core.config import Settings
from wild_catalog.core.errors import ModelUnavailableError
from wild_catalog.detection.registry import build_detector


def preop_detector_model(settings: Settings | None = None) -> None:
    settings = _detector_preop_settings(settings or Settings.from_env())
    detector = build_detector(settings)

    warmup = getattr(detector, "warmup", None)

    if warmup is not None:
        warmup()
        return

    detector.locate_objects(Image.new("RGB", (256, 256), color=(128, 128, 128)))


def _detector_preop_settings(settings: Settings) -> Settings:
    return replace(
        settings,
        detector_backend=(
            "grounding-dino" if settings.detector_backend == "stub" else settings.detector_backend
        ),
    )


def main() -> None:
    try:
        preop_detector_model()
    except ModelUnavailableError as exc:
        detail = exc.debug_detail or exc.public_detail
        raise SystemExit(f"Detector model unavailable: {detail}") from None


if __name__ == "__main__":
    main()

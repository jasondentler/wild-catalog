from PIL import Image

from wild_catalog.core.config import Settings
from wild_catalog.detection.registry import build_detector


def preop_detector_model(settings: Settings | None = None) -> None:
    settings = settings or Settings.from_env()
    detector = build_detector(settings)

    detector.locate_objects(Image.new("RGB", (256, 256), color=(128, 128, 128)))


def main() -> None:
    preop_detector_model()


if __name__ == "__main__":
    main()

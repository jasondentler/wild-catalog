from wild_catalog.conversion.platform_conversion import registry
from wild_catalog.core.config import Settings


class FakePlatformImageConverter:
    def __init__(self, *, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds

    def can_convert(self, detected_format: str) -> bool:
        return True

    def convert_to_jpeg(self, source_path, output_path) -> None:
        return None


def teardown_function() -> None:
    registry.clear_platform_image_converter_cache()


def test_build_platform_image_converter_caches_detection_for_same_settings(monkeypatch) -> None:
    constructed_timeout_seconds = []

    def build_fake_converter(*, timeout_seconds: int) -> FakePlatformImageConverter:
        constructed_timeout_seconds.append(timeout_seconds)
        return FakePlatformImageConverter(timeout_seconds=timeout_seconds)

    monkeypatch.setattr(registry, "LinuxImageMagickImageConverter", build_fake_converter)

    settings = Settings(platform_image_converter="linux-imagemagick")

    first = registry.build_platform_image_converter(settings)
    second = registry.build_platform_image_converter(settings)

    assert first is second
    assert constructed_timeout_seconds == [settings.platform_conversion_timeout_seconds]


def test_build_platform_image_converter_cache_includes_timeout(monkeypatch) -> None:
    constructed_timeout_seconds = []

    def build_fake_converter(*, timeout_seconds: int) -> FakePlatformImageConverter:
        constructed_timeout_seconds.append(timeout_seconds)
        return FakePlatformImageConverter(timeout_seconds=timeout_seconds)

    monkeypatch.setattr(registry, "LinuxImageMagickImageConverter", build_fake_converter)

    first = registry.build_platform_image_converter(
        Settings(
            platform_image_converter="linux-imagemagick",
            platform_conversion_timeout_seconds=1,
        )
    )
    second = registry.build_platform_image_converter(
        Settings(
            platform_image_converter="linux-imagemagick",
            platform_conversion_timeout_seconds=2,
        )
    )

    assert first is not second
    assert constructed_timeout_seconds == [1, 2]


def test_clear_platform_image_converter_cache_allows_rebuild(monkeypatch) -> None:
    constructed_timeout_seconds = []

    def build_fake_converter(*, timeout_seconds: int) -> FakePlatformImageConverter:
        constructed_timeout_seconds.append(timeout_seconds)
        return FakePlatformImageConverter(timeout_seconds=timeout_seconds)

    monkeypatch.setattr(registry, "LinuxImageMagickImageConverter", build_fake_converter)

    settings = Settings(platform_image_converter="linux-imagemagick")
    first = registry.build_platform_image_converter(settings)

    registry.clear_platform_image_converter_cache()
    second = registry.build_platform_image_converter(settings)

    assert first is not second
    assert constructed_timeout_seconds == [
        settings.platform_conversion_timeout_seconds,
        settings.platform_conversion_timeout_seconds,
    ]

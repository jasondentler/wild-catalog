import platform
from functools import lru_cache

from wild_catalog.conversion.platform_conversion.linux_imagemagick import (
    LinuxImageMagickImageConverter,
)
from wild_catalog.conversion.platform_conversion.macos_sips import MacOSSipsImageConverter
from wild_catalog.conversion.platform_conversion.noop import NoopPlatformImageConverter
from wild_catalog.conversion.platform_conversion.protocols import PlatformImageConverter
from wild_catalog.conversion.platform_conversion.windows_imagemagick import (
    WindowsImageMagickImageConverter,
)
from wild_catalog.core.config import Settings


def build_platform_image_converter(settings: Settings) -> PlatformImageConverter:
    return _build_platform_image_converter(
        enable_platform_image_conversion=settings.enable_platform_image_conversion,
        platform_image_converter=settings.platform_image_converter.lower(),
        platform_conversion_timeout_seconds=settings.platform_conversion_timeout_seconds,
    )


def clear_platform_image_converter_cache() -> None:
    _build_platform_image_converter.cache_clear()


@lru_cache(maxsize=16)
def _build_platform_image_converter(
    *,
    enable_platform_image_conversion: bool,
    platform_image_converter: str,
    platform_conversion_timeout_seconds: int,
) -> PlatformImageConverter:
    if not enable_platform_image_conversion:
        return NoopPlatformImageConverter()

    if platform_image_converter == "none":
        return NoopPlatformImageConverter()

    if platform_image_converter == "macos-sips":
        return MacOSSipsImageConverter(timeout_seconds=platform_conversion_timeout_seconds)

    if platform_image_converter == "linux-imagemagick":
        return LinuxImageMagickImageConverter(timeout_seconds=platform_conversion_timeout_seconds)

    if platform_image_converter == "windows-imagemagick":
        return WindowsImageMagickImageConverter(
            timeout_seconds=platform_conversion_timeout_seconds
        )

    if platform_image_converter != "auto":
        raise ValueError(f"Unknown platform image converter: {platform_image_converter}")

    system = platform.system().lower()

    if system == "darwin":
        return MacOSSipsImageConverter(timeout_seconds=platform_conversion_timeout_seconds)

    if system == "linux":
        return LinuxImageMagickImageConverter(timeout_seconds=platform_conversion_timeout_seconds)

    if system == "windows":
        return WindowsImageMagickImageConverter(
            timeout_seconds=platform_conversion_timeout_seconds
        )

    return NoopPlatformImageConverter()

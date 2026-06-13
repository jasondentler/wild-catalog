from wild_catalog.core.errors import (
    PlatformConversionError as CorePlatformConversionError,
)
from wild_catalog.core.errors import (
    UnprocessableImageError,
    UnsupportedMediaTypeError,
    WildCatalogError,
)


class ImageConversionError(WildCatalogError):
    """Base error for image conversion failures."""


class UnsupportedImageFormatError(UnsupportedMediaTypeError, ImageConversionError):
    """Raised when the uploaded image format is unsupported."""


class ImageTooLargeError(UnprocessableImageError, ImageConversionError):
    """Raised when the uploaded file or decoded image exceeds configured limits."""

    code = "image_too_large"
    message = "Decoded image exceeds the configured pixel limit."

    def __init__(self, pixel_limit: int = 0) -> None:
        message = self.message
        if pixel_limit:
            message = (
                "Decoded image exceeds the configured pixel limit "
                f"of {pixel_limit / 1_000_000:.2f} MP."
            )

        super().__init__(message)


class InvalidImageError(UnprocessableImageError, ImageConversionError):
    """Raised when image bytes cannot be decoded as the detected image type."""


class PlatformConversionError(CorePlatformConversionError, ImageConversionError):
    """Raised when an optional platform converter fails."""

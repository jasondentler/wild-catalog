from wild_catalog.core.errors import (
    PayloadTooLargeError,
    UnprocessableImageError,
    UnsupportedMediaTypeError,
    WildCatalogError,
)
from wild_catalog.core.errors import (
    PlatformConversionError as CorePlatformConversionError,
)


class ImageConversionError(WildCatalogError):
    """Base error for image conversion failures."""


class UnsupportedImageFormatError(UnsupportedMediaTypeError, ImageConversionError):
    """Raised when the uploaded image format is unsupported."""


class ImageTooLargeError(PayloadTooLargeError, ImageConversionError):
    """Raised when the uploaded file or decoded image exceeds configured limits."""


class InvalidImageError(UnprocessableImageError, ImageConversionError):
    """Raised when image bytes cannot be decoded as the detected image type."""


class PlatformConversionError(CorePlatformConversionError, ImageConversionError):
    """Raised when an optional platform converter fails."""

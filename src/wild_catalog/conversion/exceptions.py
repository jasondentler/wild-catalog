class ImageConversionError(Exception):
    """Base error for image conversion failures."""


class UnsupportedImageFormatError(ImageConversionError):
    """Raised when the uploaded image format is unsupported."""


class ImageTooLargeError(ImageConversionError):
    """Raised when the uploaded file or decoded image exceeds configured limits."""


class InvalidImageError(ImageConversionError):
    """Raised when image bytes cannot be decoded as the detected image type."""


class PlatformConversionError(ImageConversionError):
    """Raised when an optional platform converter fails."""

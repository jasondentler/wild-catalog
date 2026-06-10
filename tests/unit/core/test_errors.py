from wild_catalog.core.errors import (
    ModelUnavailableError,
    PayloadTooLargeError,
    PlatformConversionError,
    UnsupportedMediaTypeError,
)


def test_payload_too_large_error_has_expected_metadata() -> None:
    error = PayloadTooLargeError()

    assert error.code == "payload_too_large"
    assert error.status_code == 413
    assert error.public_detail == "Uploaded file exceeds the configured size limit."


def test_unsupported_media_type_error_has_expected_metadata() -> None:
    error = UnsupportedMediaTypeError()

    assert error.code == "unsupported_image_format"
    assert error.status_code == 415


def test_platform_conversion_error_keeps_debug_detail_out_of_public_detail() -> None:
    error = PlatformConversionError(
        public_detail="Image conversion failed.",
        debug_detail="raw stderr here",
    )

    assert error.public_detail == "Image conversion failed."
    assert error.debug_detail == "raw stderr here"


def test_model_unavailable_error_maps_to_503() -> None:
    error = ModelUnavailableError()

    assert error.code == "model_unavailable"
    assert error.status_code == 503

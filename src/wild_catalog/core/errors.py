from fastapi import HTTPException


class WildCatalogError(Exception):
    code = "wild_catalog_error"
    message = "Wild Catalog request failed."
    status_code = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        public_detail: str | None = None,
        debug_detail: str | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.public_detail = public_detail or message or self.message
        self.debug_detail = debug_detail

    def to_fastapi(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail=self.public_detail or self.message,
        )

class BadRequestError(WildCatalogError):
    code = "bad_request"
    message = "Bad request."
    status_code = 400

class ContentLengthHeaderMissingError(BadRequestError):
    code = "content_length_missing"
    message = "Required content-length header is missing"

class ContentLengthHeaderIsNotNumberError(BadRequestError):
    code = "content_length_NaN"
    message = "Content-length header was not a number"


class InvalidContentLanguageError(BadRequestError):
    code = "content_language_invalid"
    message = "Content-language header is invalid"


class ImagePartMissingError(BadRequestError):
    code = "image_part_missing"
    message = "Required image part missing from multipart request"


class MalformedJsonPayloadError(BadRequestError):
    code = "malformed_json_payload"
    message = "Malformed JSON payload."


class InvalidGpsOverrideError(BadRequestError):
    code = "invalid_gps_override"
    message = "Invalid GPS override."


class NotAcceptableResponseError(WildCatalogError):
    code = "not_acceptable"
    message = "Requested response format is not acceptable."
    status_code = 406


class PayloadTooLargeError(WildCatalogError):
    def __init__(self, size_limit: int = 0):
        message = self.message
        if size_limit:
            message = f"Uploaded file exceeds the configured size limit of {size_limit:,} bytes."

        super().__init__(message)

    code = "payload_too_large"
    message = "Uploaded file exceeds the configured size limit."
    status_code = 413


class UnsupportedMediaTypeError(WildCatalogError):
    code = "unsupported_image_format"
    message = "Unsupported image format."
    status_code = 415


class UnprocessableImageError(WildCatalogError):
    code = "unprocessable_image"
    message = "The image could not be processed."
    status_code = 422


class PlatformConversionError(UnprocessableImageError):
    code = "platform_conversion_failed"
    message = "Image conversion failed."


class ServiceUnavailableError(WildCatalogError):
    code = "service_unavailable"
    message = "A required model or local data file is unavailable."
    status_code = 503


class ModelUnavailableError(ServiceUnavailableError):
    code = "model_unavailable"
    message = "A required model is unavailable."


class LocalDataUnavailableError(ServiceUnavailableError):
    code = "local_data_unavailable"
    message = "Required local data is unavailable."

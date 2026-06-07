from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

from PIL import Image

from wild_catalog.conversion.exceptions import (
    ImageTooLargeError,
    PlatformConversionError,
    UnsupportedImageFormatError,
)
from wild_catalog.conversion.exif import extract_metadata
from wild_catalog.conversion.format_sniffing import (
    RAW_FORMATS,
    ImageFormat,
    sniff_image_format,
)
from wild_catalog.conversion.platform_conversion.registry import build_platform_image_converter
from wild_catalog.conversion.raw import decode_raw_image
from wild_catalog.conversion.standard import STANDARD_FORMATS, decode_standard_image
from wild_catalog.conversion.types import ConvertedImage, ExtractedMetadata
from wild_catalog.core.config import Settings
from wild_catalog.core.types import GpsCoordinates


class ImageConversionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._platform_converter = build_platform_image_converter(settings)

    def convert(self, image_file: BinaryIO) -> Image.Image:
        return self.process_and_extract_metadata(
            image_file=image_file,
            original_filename="upload",
        ).image

    def process_and_extract_metadata(
        self,
        image_file: BinaryIO,
        original_filename: str,
        gps_coordinates_override: GpsCoordinates | None = None,
        captured_at_override: datetime | None = None,
    ) -> ConvertedImage:
        file_bytes = self._read_upload_bytes(image_file)
        detected_format = sniff_image_format(file_bytes, original_filename)
        metadata = extract_metadata_from_bytes(file_bytes)

        if detected_format in STANDARD_FORMATS:
            image = decode_standard_image(
                file_bytes,
                max_image_pixels=self._settings.max_image_pixels,
            )
        elif detected_format in RAW_FORMATS:
            image = decode_raw_image(
                file_bytes,
                detected_format=detected_format,
                max_image_pixels=self._settings.max_image_pixels,
            )
        elif detected_format in {ImageFormat.HEIC, ImageFormat.HEIF}:
            image = self._convert_platform_image_to_rgb(
                file_bytes=file_bytes,
                detected_format=detected_format,
                original_filename=original_filename,
            )
        else:
            raise UnsupportedImageFormatError(f"Unsupported image format: {detected_format}")

        return ConvertedImage(
            image=image,
            original_filename=metadata.original_filename or original_filename,
            gps_coordinates=(
                gps_coordinates_override
                if gps_coordinates_override is not None
                else metadata.gps_coordinates
            ),
            captured_at=captured_at_override
            if captured_at_override is not None
            else metadata.captured_at,
            detected_format=detected_format.value,
        )

    def _read_upload_bytes(self, image_file: BinaryIO) -> bytes:
        image_file.seek(0)
        file_bytes = image_file.read()
        image_file.seek(0)

        if len(file_bytes) > self._settings.max_upload_bytes:
            raise ImageTooLargeError(
                f"Upload has {len(file_bytes)} bytes, "
                f"which exceeds limit {self._settings.max_upload_bytes}."
            )

        return file_bytes

    def _convert_platform_image_to_rgb(
        self,
        *,
        file_bytes: bytes,
        detected_format: ImageFormat,
        original_filename: str,
    ) -> Image.Image:
        if not self._platform_converter.can_convert(detected_format.value):
            raise UnsupportedImageFormatError(
                "HEIC/HEIF files are not decoded directly. Configure a platform "
                "image converter or convert the file to JPEG before upload."
            )

        suffix = Path(original_filename).suffix or f".{detected_format.value}"

        try:
            with TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                source_path = temp_path / f"source{suffix}"
                output_path = temp_path / "converted.jpg"

                source_path.write_bytes(file_bytes)
                self._platform_converter.convert_to_jpeg(
                    source_path=source_path,
                    output_path=output_path,
                )
                converted_bytes = output_path.read_bytes()

            return decode_standard_image(
                converted_bytes,
                max_image_pixels=self._settings.max_image_pixels,
            )
        except UnsupportedImageFormatError:
            raise
        except Exception as exc:
            raise PlatformConversionError("Platform image conversion failed.") from exc


def extract_metadata_from_bytes(file_bytes: bytes) -> ExtractedMetadata:
    return extract_metadata(BytesIO(file_bytes))

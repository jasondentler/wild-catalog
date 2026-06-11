from datetime import datetime
from io import BytesIO
from typing import BinaryIO

from PIL import Image

from wild_catalog.conversion.exceptions import ImageTooLargeError
from wild_catalog.conversion.exif import extract_metadata
from wild_catalog.conversion.format_sniffers.format_sniffer_chain import (
    build_format_sniffer_chain,
)
from wild_catalog.conversion.format_sniffing import sniff_image_format
from wild_catalog.conversion.types import ConvertedImage, ExtractedMetadata
from wild_catalog.core.settings import Settings
from wild_catalog.core.types import GpsCoordinates


class ImageConversionService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

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
        converter = build_format_sniffer_chain().handle(
            file_bytes,
            original_filename,
        )
        image = converter.convert(file_bytes)
        self._ensure_image_within_limits(image)

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
        file_bytes = bytearray()

        while True:
            chunk = image_file.read(64 * 1024)
            if not chunk:
                break

            file_bytes.extend(chunk)
            if len(file_bytes) > self._settings.max_upload_bytes:
                image_file.seek(0)
                raise ImageTooLargeError(
                    f"Upload has {len(file_bytes)} bytes, "
                    f"which exceeds limit {self._settings.max_upload_bytes}."
                )

        image_file.seek(0)

        return bytes(file_bytes)

    def _ensure_image_within_limits(self, image: Image.Image) -> None:
        width, height = image.size
        if width * height > self._settings.max_image_pixels:
            raise ImageTooLargeError(
                f"Decoded image has {width * height} pixels, "
                f"which exceeds limit {self._settings.max_image_pixels}."
            )


def extract_metadata_from_bytes(file_bytes: bytes) -> ExtractedMetadata:
    return extract_metadata(BytesIO(file_bytes))

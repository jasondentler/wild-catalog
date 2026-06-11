from collections.abc import AsyncGenerator
from io import BytesIO

from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.settings import Settings
from wild_catalog.pipeline.identify_command import IdentifyCommand
from wild_catalog.pipeline.identify_result import IdentifyResult


class IdentifyPipeline:
    def __init__(self, settings: Settings, conversion: ImageConversionService):
        self._settings = settings
        self._conversion = conversion

    async def execute(
        self,
        command: IdentifyCommand,
        image_stream: AsyncGenerator[bytes],
    ) -> IdentifyResult:
        image_bytes = bytearray()
        async for chunk in image_stream:
            image_bytes.extend(chunk)

        converted = self._conversion.process_and_extract_metadata(
            image_file=BytesIO(bytes(image_bytes)),
            original_filename=command.original_filename,
            gps_coordinates_override=(
                command.exif_override.gps_coordinates
                if command.exif_override is not None
                else None
            ),
            captured_at_override=(
                command.exif_override.captured_at
                if command.exif_override is not None
                else None
            ),
        )
        _ = converted
        return IdentifyResult([], False)

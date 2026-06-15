import asyncio
from types import SimpleNamespace

from wild_catalog.core.types import GpsCoordinates
from wild_catalog.pipeline.identify_command import ExifOverride, IdentifyCommand
from wild_catalog.pipeline.identify_pipeline import IdentifyPipeline


class _Conversion:
    def __init__(self) -> None:
        self.calls = []

    def process_and_extract_metadata(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace()


def test_identify_pipeline_reads_stream_and_forwards_exif_override() -> None:
    async def run():
        conversion = _Conversion()
        pipeline = IdentifyPipeline(SimpleNamespace(), conversion)
        command = IdentifyCommand(
            original_filename="image.jpg",
            exif_override=ExifOverride(
                gps_coordinates=GpsCoordinates(latitude=1.0, longitude=2.0),
                captured_at=None,
            ),
        )

        async def stream():
            yield b"abc"
            yield b"def"

        result = await pipeline.execute(command, stream())
        return result, conversion

    result, conversion = asyncio.run(run())

    assert result.objects == ()
    assert result.gps_coordinates is None
    assert conversion.calls[0]["original_filename"] == "image.jpg"
    assert conversion.calls[0]["image_file"].getvalue() == b"abcdef"
    assert conversion.calls[0]["gps_coordinates_override"] == GpsCoordinates(
        latitude=1.0,
        longitude=2.0,
    )

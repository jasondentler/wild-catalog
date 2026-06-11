from collections.abc import AsyncGenerator

from wild_catalog.pipeline.identify_command import IdentifyCommand
from wild_catalog.pipeline.identify_result import IdentifyResult


class IdentifyPipeline:

    @staticmethod
    def execute(identify_command: IdentifyCommand,
                image_stream: AsyncGenerator[bytes]) -> IdentifyResult:
        return IdentifyResult([], False)

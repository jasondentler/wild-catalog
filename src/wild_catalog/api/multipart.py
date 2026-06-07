from fastapi.responses import Response

from wild_catalog.pipeline.models import IdentifyResult


def build_multipart_response(
    result: IdentifyResult,
    *,
    include_images: bool,
) -> Response:
    raise NotImplementedError("Multipart responses are not implemented yet.")

from collections.abc import Callable
from typing import Any

from wild_catalog.wildlife_detection.optional_dependency_stubs import (
    install_pytorch_wildlife_import_stubs,
)

ModelFactory = Callable[..., Any]


def get_megadetector_v6_factory() -> ModelFactory:
    install_pytorch_wildlife_import_stubs()

    from PytorchWildlife.models import detection as pw_detection

    for model_name in ("MegaDetectorV6Apache", "MegaDetectorV6"):
        model_factory = getattr(pw_detection, model_name, None)
        if model_factory is not None:
            return model_factory

    raise ImportError("PytorchWildlife does not expose a MegaDetector v6 model")

import importlib.util
import sys
import types
from importlib.machinery import ModuleSpec

from wild_catalog.wildlife_detection.missing_optional_predictor import (
    MissingOptionalPredictor,
    missing_optional_model_function,
)
from wild_catalog.wildlife_detection.noop_summary_writer import NoopSummaryWriter


def install_pytorch_wildlife_import_stubs() -> None:
    for module_name in ("soundfile", "librosa"):
        if _module_needs_stub(module_name):
            _ensure_module(module_name)

    if _module_needs_stub("yolov5"):
        general_module = _ensure_module("yolov5.utils.general")
        general_module.non_max_suppression = missing_optional_model_function
        general_module.scale_boxes = missing_optional_model_function

    if _module_needs_stub("ultralytics"):
        yolo_module = _ensure_module("ultralytics.models.yolo")
        yolo_detect_module = _ensure_module("ultralytics.models.yolo.detect")
        rtdetr_module = _ensure_module("ultralytics.models.rtdetr")
        yolo_module.detect = yolo_detect_module
        yolo_detect_module.DetectionPredictor = MissingOptionalPredictor
        rtdetr_module.RTDETRPredictor = MissingOptionalPredictor

    if _tensorboard_needs_stub():
        tensorboard_module = _ensure_module("tensorboard")
        tensorboard_module.__version__ = "1.15"
        _ensure_module("tensorboard.backend.event_processing")
        torch_tensorboard_module = _ensure_torch_tensorboard_module()
        torch_tensorboard_module.SummaryWriter = NoopSummaryWriter


def _tensorboard_needs_stub() -> bool:
    module = sys.modules.get("tensorboard")
    if module is not None:
        return getattr(module, "__spec__", None) is None or not hasattr(module, "__version__")

    return importlib.util.find_spec("tensorboard") is None


def _module_needs_stub(module_name: str) -> bool:
    module = sys.modules.get(module_name)
    if module is not None:
        return getattr(module, "__spec__", None) is None

    return importlib.util.find_spec(module_name) is None


def _ensure_module(module_name: str) -> types.ModuleType:
    module = sys.modules.get(module_name)
    if module is not None:
        if getattr(module, "__spec__", None) is None:
            module.__spec__ = ModuleSpec(module_name, loader=None, is_package=True)
        if not hasattr(module, "__path__"):
            module.__path__ = []
        return module

    module = types.ModuleType(module_name)
    module.__path__ = []
    module.__spec__ = ModuleSpec(module_name, loader=None, is_package=True)
    sys.modules[module_name] = module

    parent_name, _, child_name = module_name.rpartition(".")
    if parent_name:
        parent_module = _ensure_module(parent_name)
        setattr(parent_module, child_name, module)

    return module


def _ensure_torch_tensorboard_module() -> types.ModuleType:
    module_name = "torch.utils.tensorboard"
    module = sys.modules.get(module_name)
    if module is not None:
        return module

    import torch.utils as torch_utils

    module = types.ModuleType(module_name)
    module.__spec__ = ModuleSpec(module_name, loader=None, is_package=False)
    sys.modules[module_name] = module
    torch_utils.tensorboard = module
    return module

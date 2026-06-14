import sys
import types
from importlib.machinery import ModuleSpec
from unittest.mock import MagicMock


def _stub_module(module_name: str, *, package: bool = True) -> types.ModuleType:
    module = sys.modules.get(module_name)
    if not isinstance(module, types.ModuleType):
        module = types.ModuleType(module_name)
        sys.modules[module_name] = module

    module.__spec__ = ModuleSpec(module_name, loader=None, is_package=package)
    if package:
        module.__path__ = []

    parent_name, _, child_name = module_name.rpartition(".")
    if parent_name:
        parent_module = _stub_module(parent_name)
        setattr(parent_module, child_name, module)

    return module


def _stub_torch_tensorboard() -> types.ModuleType:
    import torch.utils as torch_utils

    module_name = "torch.utils.tensorboard"
    module = types.ModuleType(module_name)
    module.__spec__ = ModuleSpec(module_name, loader=None, is_package=False)
    sys.modules[module_name] = module
    torch_utils.tensorboard = module
    return module


# Intercept optional audio sub-dependencies before PytorchWildlife loads.
_stub_module("soundfile")
_stub_module("librosa")
_stub_module("pydub")

# Mock out YOLO packages that are intentionally excluded from the runtime dependency set.
general_module = _stub_module("yolov5.utils.general")
general_module.non_max_suppression = MagicMock()
general_module.scale_boxes = MagicMock()

yolo_module = _stub_module("ultralytics.models.yolo")
yolo_detect_module = _stub_module("ultralytics.models.yolo.detect")
rtdetr_module = _stub_module("ultralytics.models.rtdetr")
yolo_module.detect = yolo_detect_module
yolo_detect_module.DetectionPredictor = MagicMock()
rtdetr_module.RTDETRPredictor = MagicMock()
_stub_module("ultralytics.utils")
_stub_module("ultralytics.engine")
_stub_module("ultralytics.engine.results")

# TensorBoard is imported by the RT-DETR config package, but inference does not use it.
tensorboard_module = _stub_module("tensorboard")
tensorboard_module.__version__ = "1.15"
_stub_module("tensorboard.backend")
_stub_module("tensorboard.backend.event_processing")
torch_tensorboard_module = _stub_torch_tensorboard()
torch_tensorboard_module.SummaryWriter = MagicMock()
torch_tensorboard_module.FileWriter = MagicMock()
torch_tensorboard_module.RecordWriter = MagicMock()

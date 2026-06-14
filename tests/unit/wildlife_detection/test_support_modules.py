import sys
import types
from importlib.machinery import ModuleSpec
from types import SimpleNamespace

import pytest

from wild_catalog.wildlife_detection import megadetector_factory
from wild_catalog.wildlife_detection.missing_optional_predictor import (
    MissingOptionalPredictor,
    missing_optional_model_function,
)
from wild_catalog.wildlife_detection.noop_summary_writer import NoopSummaryWriter
from wild_catalog.wildlife_detection.optional_dependency_stubs import (
    install_pytorch_wildlife_import_stubs,
)
from wild_catalog.wildlife_detection.pytorch_wildlife_stdout import (
    suppress_pytorch_wildlife_model_load_stdout,
)
from wild_catalog.wildlife_detection.torch_hub_cache import configure_torch_hub_dir


def test_missing_optional_predictor_raises_import_error() -> None:
    with pytest.raises(ImportError, match="optional YOLO"):
        MissingOptionalPredictor("unused", key="unused")


def test_missing_optional_model_function_raises_import_error() -> None:
    with pytest.raises(ImportError, match="optional YOLO"):
        missing_optional_model_function("unused", key="unused")


def test_noop_summary_writer_supports_context_and_ignored_methods() -> None:
    writer = NoopSummaryWriter("unused", key="unused")

    assert writer.add_scalar("metric", 1.0) is None
    with writer as entered:
        assert entered is writer
    assert writer.__exit__(None, None, None) is None


def test_stdout_filter_suppresses_only_pytorch_wildlife_load_lines(capsys) -> None:
    with suppress_pytorch_wildlife_model_load_stdout():
        print("before")
        print("Load PResNet101 state_dict")
        print("after", end="")

    assert capsys.readouterr().out == "before\nafter"


def test_configure_torch_hub_dir_respects_torch_home(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TORCH_HOME", str(tmp_path / "torch-home"))
    torch_module = SimpleNamespace(hub=SimpleNamespace(set_dir=lambda value: None))
    monkeypatch.setitem(sys.modules, "torch", torch_module)

    configure_torch_hub_dir(tmp_path / "unused")

    assert not (tmp_path / "unused").exists()


def test_configure_torch_hub_dir_sets_writable_cache(monkeypatch, tmp_path) -> None:
    selected = {}
    torch_module = SimpleNamespace(
        hub=SimpleNamespace(set_dir=lambda value: selected.setdefault("dir", value))
    )
    monkeypatch.delenv("TORCH_HOME", raising=False)
    monkeypatch.setitem(sys.modules, "torch", torch_module)

    configure_torch_hub_dir(tmp_path / "torch-hub")

    assert selected == {"dir": str(tmp_path / "torch-hub")}
    assert (tmp_path / "torch-hub").is_dir()


def test_install_pytorch_wildlife_import_stubs_creates_missing_modules(monkeypatch) -> None:
    _remove_stubbed_modules(monkeypatch)
    monkeypatch.setattr("importlib.util.find_spec", lambda module_name: None)
    torch_utils = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "torch.utils", torch_utils)

    install_pytorch_wildlife_import_stubs()

    assert sys.modules["librosa"].__spec__ is not None
    assert sys.modules["soundfile"].__spec__ is not None
    assert sys.modules["yolov5.utils.general"].non_max_suppression is (
        missing_optional_model_function
    )
    assert sys.modules["ultralytics.models.yolo"].detect is sys.modules[
        "ultralytics.models.yolo.detect"
    ]
    assert sys.modules["ultralytics.models.yolo.detect"].DetectionPredictor is (
        MissingOptionalPredictor
    )
    assert sys.modules["ultralytics.models.rtdetr"].RTDETRPredictor is MissingOptionalPredictor
    assert sys.modules["tensorboard"].__version__ == "1.15"
    assert sys.modules["torch.utils.tensorboard"].SummaryWriter is NoopSummaryWriter
    assert hasattr(torch_utils, "tensorboard") or "torch" in sys.modules


def test_install_pytorch_wildlife_import_stubs_repairs_existing_modules(monkeypatch) -> None:
    _remove_stubbed_modules(monkeypatch)
    monkeypatch.setattr("importlib.util.find_spec", lambda module_name: None)
    monkeypatch.setitem(sys.modules, "librosa", types.ModuleType("librosa"))
    monkeypatch.setitem(sys.modules, "tensorboard", types.ModuleType("tensorboard"))
    torch_tensorboard = types.ModuleType("torch.utils.tensorboard")
    monkeypatch.setitem(sys.modules, "torch.utils.tensorboard", torch_tensorboard)

    install_pytorch_wildlife_import_stubs()

    assert sys.modules["librosa"].__spec__ is not None
    assert sys.modules["tensorboard"].__version__ == "1.15"
    assert torch_tensorboard.SummaryWriter is NoopSummaryWriter


def test_install_pytorch_wildlife_import_stubs_leaves_real_modules_alone(monkeypatch) -> None:
    _remove_stubbed_modules(monkeypatch)
    existing = types.ModuleType("librosa")
    existing.__spec__ = ModuleSpec("librosa", loader=None, is_package=True)
    monkeypatch.setitem(sys.modules, "librosa", existing)

    install_pytorch_wildlife_import_stubs()

    assert sys.modules["librosa"] is existing


def test_get_megadetector_v6_factory_prefers_apache_detector(monkeypatch) -> None:
    apache_factory = object()
    fallback_factory = object()
    detection_module = SimpleNamespace(
        MegaDetectorV6Apache=apache_factory,
        MegaDetectorV6=fallback_factory,
    )

    monkeypatch.setattr(megadetector_factory, "install_pytorch_wildlife_import_stubs", lambda: None)
    _install_pytorch_wildlife_test_modules(monkeypatch, detection_module)

    assert megadetector_factory.get_megadetector_v6_factory() is apache_factory


def test_get_megadetector_v6_factory_raises_when_model_is_absent(monkeypatch) -> None:
    detection_module = SimpleNamespace()

    monkeypatch.setattr(megadetector_factory, "install_pytorch_wildlife_import_stubs", lambda: None)
    _install_pytorch_wildlife_test_modules(monkeypatch, detection_module)

    with pytest.raises(ImportError, match="MegaDetector v6"):
        megadetector_factory.get_megadetector_v6_factory()


def _remove_stubbed_modules(monkeypatch) -> None:
    for module_name in list(sys.modules):
        if module_name in {
            "librosa",
            "soundfile",
            "tensorboard",
        } or module_name.startswith(
            (
                "PytorchWildlife",
                "torch.utils.tensorboard",
                "ultralytics",
                "yolov5",
            )
        ):
            monkeypatch.delitem(sys.modules, module_name, raising=False)


def _install_pytorch_wildlife_test_modules(monkeypatch, detection_module) -> None:
    package_module = types.ModuleType("PytorchWildlife")
    models_module = types.ModuleType("PytorchWildlife.models")
    package_module.__path__ = []
    models_module.__path__ = []
    models_module.detection = detection_module

    monkeypatch.setitem(sys.modules, "PytorchWildlife", package_module)
    monkeypatch.setitem(sys.modules, "PytorchWildlife.models", models_module)
    monkeypatch.setitem(sys.modules, "PytorchWildlife.models.detection", detection_module)

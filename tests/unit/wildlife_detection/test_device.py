import builtins
from types import SimpleNamespace

from wild_catalog.wildlife_detection.device import get_torch_device


def test_get_torch_device_prefers_mps() -> None:
    torch_module = SimpleNamespace(
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
        cuda=SimpleNamespace(is_available=lambda: True),
    )

    assert get_torch_device(torch_module) == "mps"


def test_get_torch_device_uses_cuda_when_mps_is_unavailable() -> None:
    torch_module = SimpleNamespace(
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
        cuda=SimpleNamespace(is_available=lambda: True),
    )

    assert get_torch_device(torch_module) == "cuda"


def test_get_torch_device_falls_back_to_cpu() -> None:
    torch_module = SimpleNamespace(
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False)),
        cuda=SimpleNamespace(is_available=lambda: False),
    )

    assert get_torch_device(torch_module) == "cpu"


def test_get_torch_device_falls_back_to_cpu_when_capability_checks_are_missing() -> None:
    torch_module = SimpleNamespace(backends=SimpleNamespace(mps=object()), cuda=object())

    assert get_torch_device(torch_module) == "cpu"


def test_get_torch_device_falls_back_to_cpu_when_torch_is_not_installed(
    monkeypatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert get_torch_device() == "cpu"

from wild_catalog.core import device


def setup_function() -> None:
    device.get_torch_device.cache_clear()


def teardown_function() -> None:
    device.get_torch_device.cache_clear()


def configure_available_devices(
    monkeypatch,
    *,
    mps_available: bool,
    cuda_available: bool,
) -> None:
    monkeypatch.setattr(device.torch.backends.mps, "is_available", lambda: mps_available)
    monkeypatch.setattr(device.torch.cuda, "is_available", lambda: cuda_available)


def test_get_torch_device_prefers_mps(monkeypatch) -> None:
    configure_available_devices(
        monkeypatch,
        mps_available=True,
        cuda_available=True,
    )

    assert device.get_torch_device().type == "mps"


def test_get_torch_device_uses_cuda_when_mps_unavailable(monkeypatch) -> None:
    configure_available_devices(
        monkeypatch,
        mps_available=False,
        cuda_available=True,
    )

    assert device.get_torch_device().type == "cuda"


def test_get_torch_device_falls_back_to_cpu(monkeypatch) -> None:
    configure_available_devices(
        monkeypatch,
        mps_available=False,
        cuda_available=False,
    )

    assert device.get_torch_device().type == "cpu"


def test_get_torch_device_caches_selected_device(monkeypatch) -> None:
    cuda_checks = 0

    monkeypatch.setattr(device.torch.backends.mps, "is_available", lambda: False)

    def is_cuda_available() -> bool:
        nonlocal cuda_checks
        cuda_checks += 1
        return False

    monkeypatch.setattr(device.torch.cuda, "is_available", is_cuda_available)

    assert device.get_torch_device().type == "cpu"
    assert device.get_torch_device().type == "cpu"
    assert cuda_checks == 1

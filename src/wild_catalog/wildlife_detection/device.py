from typing import Any


def get_torch_device(torch_module: Any | None = None) -> str:
    """Return the preferred available PyTorch device name."""
    if torch_module is None:
        try:
            import torch as torch_module
        except ImportError:
            return "cpu"

    backends = getattr(torch_module, "backends", None)
    mps = getattr(backends, "mps", None)
    if (
        mps is not None
        and callable(getattr(mps, "is_available", None))
        and mps.is_available()
    ):
        return "mps"

    cuda = getattr(torch_module, "cuda", None)
    if cuda is not None and callable(getattr(cuda, "is_available", None)) and cuda.is_available():
        return "cuda"

    return "cpu"

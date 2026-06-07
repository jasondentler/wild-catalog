from functools import lru_cache

import torch


@lru_cache(maxsize=1)
def get_torch_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")

    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")

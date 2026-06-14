import os
from pathlib import Path


def configure_torch_hub_dir(torch_hub_dir: Path) -> None:
    if os.getenv("TORCH_HOME") is not None:
        return

    import torch

    torch_hub_dir.mkdir(parents=True, exist_ok=True)
    torch.hub.set_dir(str(torch_hub_dir))

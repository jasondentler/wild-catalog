from collections.abc import Callable
from typing import Any


class NoopSummaryWriter:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs

    def __getattr__(self, name: str) -> Callable[..., None]:
        _ = name
        return _noop

    def __enter__(self) -> "NoopSummaryWriter":
        return self

    def __exit__(self, *args: Any) -> None:
        _ = args


def _noop(*args: Any, **kwargs: Any) -> None:
    _ = args, kwargs

from typing import Any


class MissingOptionalPredictor:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs
        raise ImportError("Install the optional YOLO backend dependencies to use this detector")


def missing_optional_model_function(*args: Any, **kwargs: Any) -> None:
    _ = args, kwargs
    raise ImportError("Install the optional YOLO backend dependencies to use this detector")

from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image


class Converter(ABC):
    @abstractmethod
    def convert(self, file_bytes: bytes) -> Image.Image:
        pass  # pragma: no cover

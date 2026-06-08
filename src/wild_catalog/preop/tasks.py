from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


class PreOperationalTask(Protocol):
    name: str

    def run(self) -> None:
        ...


@dataclass(frozen=True, slots=True)
class FunctionPreOperationalTask:
    name: str
    action: Callable[[], None]

    def run(self) -> None:
        self.action()

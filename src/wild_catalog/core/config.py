from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    env: str = "development"

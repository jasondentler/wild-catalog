from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundingBox:
    xmin: int
    ymin: int
    xmax: int
    ymax: int

    @property
    def width(self) -> int:
        return self.xmax - self.xmin

    @property
    def height(self) -> int:
        return self.ymax - self.ymin


@dataclass(frozen=True, slots=True)
class GpsCoordinates:
    latitude: float
    longitude: float

from pydantic import BaseModel


class BoundingBoxResponse(BaseModel):
    xmin: int
    ymin: int
    xmax: int
    ymax: int
    width: int
    height: int

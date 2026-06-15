from pydantic import BaseModel


class PredictionResponse(BaseModel):
    confidence: float
    is_present: bool
    taxonomy: list[str]
    taxonomy_common_names: list[str]

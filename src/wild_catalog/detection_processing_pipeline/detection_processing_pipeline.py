from wild_catalog.core.types import Detection
from wild_catalog.identify_pipeline.identified_object import IdentifiedObject
from wild_catalog.identify_pipeline.prediction import Prediction


class DetectionProcessingPipeline:
    def process(self, detection: Detection) -> IdentifiedObject:
        label_taxonomy = (detection.label,) if detection.label is not None else ()
        prediction = Prediction(
            confidence=detection.confidence,
            is_present=False,
            taxonomy=label_taxonomy,
            taxonomy_common_names=label_taxonomy,
            class_id=detection.class_id,
        )

        return IdentifiedObject(
            detection.box,
            detection.box,
            (prediction,),
            None,
        )

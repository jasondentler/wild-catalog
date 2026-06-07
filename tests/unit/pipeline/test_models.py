from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyResult
from wild_catalog.taxonomy.types import EnrichedPrediction


def test_identify_result_can_contain_identified_objects() -> None:
    prediction = EnrichedPrediction(
        confidence=0.98,
        is_present=True,
        taxonomy=(
            "Animalia",
            "Chordata",
            "Aves",
            "Passeriformes",
            "Corvidae",
            "Cyanocitta cristata",
        ),
        taxonomy_common_names=(
            "Animals",
            "Chordates",
            "Birds",
            "Perching Birds",
            "Crows and Jays",
            "Blue Jay",
        ),
    )

    identified_object = IdentifiedObject(
        bounding_box=BoundingBox(xmin=10, ymin=20, xmax=30, ymax=40),
        bounding_box_with_margin=BoundingBox(xmin=5, ymin=15, xmax=35, ymax=45),
        gps_coordinates=GpsCoordinates(latitude=29.7604, longitude=-95.3698),
        predictions=(prediction,),
    )

    result = IdentifyResult(objects=(identified_object,))

    assert len(result.objects) == 1
    assert result.objects[0].predictions[0].is_present is True

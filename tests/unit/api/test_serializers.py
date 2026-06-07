from wild_catalog.api.serializers import identify_result_to_json
from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyResult
from wild_catalog.taxonomy.types import EnrichedPrediction


def test_identify_result_to_json_returns_json_compatible_response() -> None:
    result = IdentifyResult(
        objects=(
            IdentifiedObject(
                bounding_box=BoundingBox(xmin=10, ymin=20, xmax=30, ymax=50),
                bounding_box_with_margin=BoundingBox(xmin=5, ymin=15, xmax=35, ymax=55),
                gps_coordinates=GpsCoordinates(latitude=29.7604, longitude=-95.3698),
                predictions=(
                    EnrichedPrediction(
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
                    ),
                ),
            ),
        )
    )

    assert identify_result_to_json(result) == [
        {
            "bounding_box": {
                "xmin": 10,
                "ymin": 20,
                "xmax": 30,
                "ymax": 50,
                "width": 20,
                "height": 30,
            },
            "bounding_box_with_margin": {
                "xmin": 5,
                "ymin": 15,
                "xmax": 35,
                "ymax": 55,
                "width": 30,
                "height": 40,
            },
            "gps_coordinates": [29.7604, -95.3698],
            "predictions": [
                {
                    "confidence": 0.98,
                    "is_present": True,
                    "taxonomy": [
                        "Animalia",
                        "Chordata",
                        "Aves",
                        "Passeriformes",
                        "Corvidae",
                        "Cyanocitta cristata",
                    ],
                    "taxonomy_common_names": [
                        "Animals",
                        "Chordates",
                        "Birds",
                        "Perching Birds",
                        "Crows and Jays",
                        "Blue Jay",
                    ],
                }
            ],
        }
    ]

from wild_catalog.api.response_models import (
    BoundingBoxResponse,
    IdentifiedObjectResponse,
    PredictionResponse,
)


def test_identified_object_response_serializes_api_shape() -> None:
    bounding_box = BoundingBoxResponse(
        xmin=10,
        ymin=20,
        xmax=110,
        ymax=220,
        width=100,
        height=200,
    )
    response = IdentifiedObjectResponse(
        bounding_box=bounding_box,
        bounding_box_with_margin=BoundingBoxResponse(
            xmin=0,
            ymin=5,
            xmax=120,
            ymax=235,
            width=120,
            height=230,
        ),
        gps_coordinates=(45.1234, -93.1234),
        predictions=[
            PredictionResponse(
                confidence=0.92,
                is_present=True,
                taxonomy=["Animalia", "Chordata", "Mammalia"],
                taxonomy_common_names=["Animals", "Chordates", "Mammals"],
            )
        ],
    )

    assert response.model_dump() == {
        "bounding_box": {
            "xmin": 10,
            "ymin": 20,
            "xmax": 110,
            "ymax": 220,
            "width": 100,
            "height": 200,
        },
        "bounding_box_with_margin": {
            "xmin": 0,
            "ymin": 5,
            "xmax": 120,
            "ymax": 235,
            "width": 120,
            "height": 230,
        },
        "gps_coordinates": (45.1234, -93.1234),
        "predictions": [
            {
                "confidence": 0.92,
                "is_present": True,
                "taxonomy": ["Animalia", "Chordata", "Mammalia"],
                "taxonomy_common_names": ["Animals", "Chordates", "Mammals"],
            }
        ],
    }

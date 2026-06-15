from wild_catalog.api.response_models import (
    BoundingBoxResponse,
    GpsCoordinatesResponse,
    IdentifiedObjectResponse,
    IdentifyResponse,
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
        predictions=[
            PredictionResponse(
                confidence=0.92,
                is_present=True,
                taxonomy=[
                    "Animalia",
                    "Chordata",
                    "Aves",
                    "Passeriformes",
                    "Corvidae",
                    "Cyanocitta cristata",
                ],
                taxonomy_common_names=[
                    "Animals",
                    "Chordates",
                    "Birds",
                    "Perching Birds",
                    "Crows and Jays",
                    "Blue Jay",
                ],
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
        "predictions": [
            {
                "confidence": 0.92,
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


def test_identify_response_serializes_top_level_gps_and_results() -> None:
    object_response = IdentifiedObjectResponse(
        bounding_box=BoundingBoxResponse(xmin=1, ymin=2, xmax=3, ymax=4, width=2, height=2),
        bounding_box_with_margin=BoundingBoxResponse(
            xmin=0,
            ymin=1,
            xmax=4,
            ymax=5,
            width=4,
            height=4,
        ),
        predictions=[],
    )

    response = IdentifyResponse(
        gps_coordinates=GpsCoordinatesResponse(latitude=45.1234, longitude=-93.1234),
        results=[object_response],
    )

    assert response.model_dump() == {
        "gps_coordinates": {
            "latitude": 45.1234,
            "longitude": -93.1234,
        },
        "results": [object_response.model_dump()],
    }


def test_identify_response_defaults_unknown_gps_to_none() -> None:
    response = IdentifyResponse(results=[])

    assert response.model_dump() == {
        "gps_coordinates": None,
        "results": [],
    }

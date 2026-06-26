import json
from datetime import datetime

from wild_catalog.api.response_archive import IdentifyResponseArchive
from wild_catalog.identify_pipeline.identify_result import IdentifyResult


def test_response_archive_stores_response_json_with_capture_date_filename(tmp_path) -> None:
    archive = IdentifyResponseArchive(tmp_path)
    result = IdentifyResult(
        objects=(),
        original_filename="IMG_8113.jpg",
        captured_at=datetime(2026, 3, 1, 14, 30, 0),
    )
    payload = {"gps_coordinates": None, "results": []}

    path = archive.store(result, payload)

    assert path == tmp_path / "20260301-IMG_8113.json"
    assert json.loads(path.read_text()) == payload


def test_response_archive_strips_existing_date_prefix_from_filename(tmp_path) -> None:
    archive = IdentifyResponseArchive(tmp_path)
    result = IdentifyResult(
        objects=(),
        original_filename="20260402-IMG_7906.jpg",
        captured_at=datetime(2026, 4, 2, 17, 34, 8),
    )

    path = archive.store(result, {"results": []})

    assert path == tmp_path / "20260402-IMG_7906.json"


def test_response_archive_does_not_overwrite_existing_response(tmp_path) -> None:
    archive = IdentifyResponseArchive(tmp_path)
    result = IdentifyResult(
        objects=(),
        original_filename="IMG_8113.jpg",
        captured_at=datetime(2026, 3, 1, 14, 30, 0),
    )

    first_path = archive.store(result, {"results": ["first"]})
    second_path = archive.store(result, {"results": ["second"]})

    assert first_path == tmp_path / "20260301-IMG_8113.json"
    assert second_path == tmp_path / "20260301-IMG_8113-2.json"
    assert json.loads(first_path.read_text()) == {"results": ["first"]}
    assert json.loads(second_path.read_text()) == {"results": ["second"]}


def test_response_archive_skips_results_without_capture_date(tmp_path) -> None:
    archive = IdentifyResponseArchive(tmp_path)
    result = IdentifyResult(objects=(), original_filename="IMG_8113.jpg")

    path = archive.store(result, {"results": []})

    assert path is None
    assert list(tmp_path.iterdir()) == []

import pytest
from shapely.geometry import Polygon

from wild_catalog.core.config import Settings
from wild_catalog.prior.build import builder
from wild_catalog.prior.build.geopackage import RangeGeometry
from wild_catalog.prior.store import SQLiteSpeciesRangeStore

pytestmark = pytest.mark.integration


def test_build_inat21_range_map_store_with_mocked_inputs(monkeypatch, tmp_path) -> None:
    metadata_payload = b"""
    {
      "version": "test-version",
      "ranges": 1,
      "collections": {
        "birds": {
          "ranges": 1,
          "archives": 1
        }
      }
    }
    """
    fake_gpkg = tmp_path / "fake.gpkg"
    fake_gpkg.write_bytes(b"fake")

    monkeypatch.setattr(builder, "download_bytes", lambda url: metadata_payload)
    monkeypatch.setattr(
        builder,
        "download_range_map_archive",
        lambda archive, *, download_dir: fake_gpkg,
    )
    monkeypatch.setattr(
        builder,
        "iter_range_geometries",
        lambda gpkg_path: [
            RangeGeometry(
                taxon_id=101,
                geometry=_box(-96.0, 29.0, -95.0, 30.0),
            )
        ],
    )

    database_path = tmp_path / "ranges.sqlite3"
    settings = Settings(
        inat_range_maps_download_dir=tmp_path / "downloads",
        range_map_store_path=database_path,
    )

    result = builder.build_inat21_range_map_store(settings)
    store = SQLiteSpeciesRangeStore(database_path)

    try:
        assert result == database_path
        candidates = store.get_candidate_geometries_for_point(
            latitude=29.7604,
            longitude=-95.3698,
        )
    finally:
        store.close()

    assert [taxon_id for taxon_id, _ in candidates] == [101]


def test_build_inat21_range_map_store_logs_progress(monkeypatch, tmp_path, caplog) -> None:
    metadata_payload = b"""
    {
      "version": "test-version",
      "ranges": 1,
      "collections": {
        "birds": {
          "ranges": 1,
          "archives": 1
        }
      }
    }
    """
    fake_gpkg = tmp_path / "fake.gpkg"
    fake_gpkg.write_bytes(b"fake")

    monkeypatch.setattr(builder, "download_bytes", lambda url: metadata_payload)
    monkeypatch.setattr(
        builder,
        "download_range_map_archive",
        lambda archive, *, download_dir: fake_gpkg,
    )
    monkeypatch.setattr(
        builder,
        "iter_range_geometries",
        lambda gpkg_path: [
            RangeGeometry(taxon_id=101, geometry=_box(-96.0, 29.0, -95.0, 30.0)),
            RangeGeometry(taxon_id=202, geometry=_box(-80.0, 20.0, -79.0, 21.0)),
        ],
    )

    settings = Settings(
        inat_range_maps_download_dir=tmp_path / "downloads",
        range_map_store_path=tmp_path / "ranges.sqlite3",
    )

    with caplog.at_level("INFO"):
        builder.build_inat21_range_map_store(
            settings,
            progress_log_interval_seconds=0,
        )

    assert "Discovered 1 iNat range-map archive(s)" in caplog.text
    assert f"db={settings.range_map_store_path}" in caplog.text
    assert "Downloading 1 range-map archive(s) with 1 worker(s)" in caplog.text
    assert "100.0% complete (1/1 archives), ETA 0s" in caplog.text
    assert "Processed 1 geometries from iNaturalist_geomodel_birds.gpkg" in caplog.text
    assert "100.0% complete (1/1 ranges), ETA 0s" in caplog.text
    assert "Processed 2 geometries from iNaturalist_geomodel_birds.gpkg" in caplog.text
    assert "Wrote 2 range geometries" in caplog.text
    assert "Built iNat range-map SQLite store" in caplog.text


def _box(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Polygon:
    return Polygon(
        [
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat),
        ]
    )

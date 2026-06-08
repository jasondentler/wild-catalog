import pyarrow as pa
import pytest
from shapely import to_wkb
from shapely.geometry import Polygon

from wild_catalog.prior.build import geopackage
from wild_catalog.prior.build.geopackage import _find_taxon_id_column, iter_range_geometries


def test_find_taxon_id_column_matches_exact_name() -> None:
    assert _find_taxon_id_column(["taxon_id", "geometry"]) == "taxon_id"


def test_find_taxon_id_column_matches_case_insensitive_name() -> None:
    assert _find_taxon_id_column(["TaxonID", "geometry"]) == "TaxonID"


def test_find_taxon_id_column_returns_none_when_missing() -> None:
    assert _find_taxon_id_column(["name", "geometry"]) is None


def test_iter_range_geometries_reads_wkb_rows(monkeypatch, tmp_path) -> None:
    polygon = Polygon(
        [
            (-95.40, 29.70),
            (-95.30, 29.70),
            (-95.30, 29.80),
            (-95.40, 29.80),
            (-95.40, 29.70),
        ]
    )
    table = pa.table(
        {
            "taxon_id": [101, 202, None],
            "geom": [to_wkb(polygon), None, to_wkb(polygon)],
        }
    )

    monkeypatch.setattr(geopackage.pyogrio, "list_layers", lambda path: [("ranges", "Polygon")])
    monkeypatch.setattr(
        geopackage.pyogrio,
        "read_arrow",
        lambda path, *, layer: (
            {
                "crs": "EPSG:4326",
                "geometry_name": "geom",
            },
            table,
        ),
    )

    rows = list(iter_range_geometries(tmp_path / "tiny.gpkg"))

    assert len(rows) == 1
    assert rows[0].taxon_id == 101
    assert rows[0].geometry.equals(polygon)


def test_iter_range_geometries_raises_when_no_taxon_layer_exists(monkeypatch, tmp_path) -> None:
    table = pa.table({"name": ["species"], "geom": [None]})

    monkeypatch.setattr(geopackage.pyogrio, "list_layers", lambda path: [("ranges", "Polygon")])
    monkeypatch.setattr(
        geopackage.pyogrio,
        "read_arrow",
        lambda path, *, layer: (
            {
                "crs": "EPSG:4326",
                "geometry_name": "geom",
            },
            table,
        ),
    )

    with pytest.raises(ValueError, match="recognized taxon ID column"):
        list(iter_range_geometries(tmp_path / "tiny.gpkg"))

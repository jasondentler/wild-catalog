import json

from wild_catalog.prior.build.metadata import parse_range_map_metadata


def test_parse_range_map_metadata_builds_single_archive_url() -> None:
    payload = json.dumps(
        {
            "version": "2026-06-01",
            "ranges": 10,
            "collections": {
                "birds": {
                    "ranges": 10,
                    "archives": 1,
                },
            },
        }
    ).encode()

    metadata = parse_range_map_metadata(payload)

    assert metadata.version == "2026-06-01"
    assert metadata.ranges == 10
    assert len(metadata.archives) == 1
    assert metadata.archives[0].collection_key == "birds"
    assert metadata.archives[0].archive_index is None
    assert metadata.archives[0].filename == "iNaturalist_geomodel_birds.gpkg"
    assert metadata.archives[0].url.endswith("/iNaturalist_geomodel_birds.gpkg")


def test_parse_range_map_metadata_builds_multi_archive_urls() -> None:
    payload = json.dumps(
        {
            "version": "2026-06-01",
            "ranges": 20,
            "collections": {
                "plants": {
                    "ranges": 20,
                    "archives": 2,
                },
            },
        }
    ).encode()

    metadata = parse_range_map_metadata(payload)

    assert [archive.archive_index for archive in metadata.archives] == [1, 2]
    assert [archive.filename for archive in metadata.archives] == [
        "iNaturalist_geomodel_plants_1.gpkg",
        "iNaturalist_geomodel_plants_2.gpkg",
    ]
    assert [archive.url.rsplit("/", maxsplit=1)[-1] for archive in metadata.archives] == [
        "iNaturalist_geomodel_plants_1.gpkg",
        "iNaturalist_geomodel_plants_2.gpkg",
    ]

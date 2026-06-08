import json
from dataclasses import dataclass
from typing import Any

BASE_GEOPACKAGE_URL = (
    "https://inaturalist-open-data.s3.us-east-1.amazonaws.com/"
    "geomodel/geopackages/latest"
)


@dataclass(frozen=True, slots=True)
class RangeMapArchive:
    collection_key: str
    archive_index: int | None
    url: str
    filename: str


@dataclass(frozen=True, slots=True)
class RangeMapMetadata:
    version: str
    ranges: int
    archives: tuple[RangeMapArchive, ...]


def parse_range_map_metadata(payload: bytes) -> RangeMapMetadata:
    raw: dict[str, Any] = json.loads(payload.decode("utf-8"))

    version = str(raw["version"])
    ranges = int(raw["ranges"])
    collections = raw["collections"]

    archives: list[RangeMapArchive] = []

    for collection_key, collection_summary in collections.items():
        archive_count = int(collection_summary["archives"])

        for index in range(archive_count):
            archive_index = index + 1 if archive_count > 1 else None
            suffix = f"_{archive_index}" if archive_index is not None else ""
            filename = f"iNaturalist_geomodel_{collection_key}{suffix}.gpkg"
            url = f"{BASE_GEOPACKAGE_URL}/{filename}"

            archives.append(
                RangeMapArchive(
                    collection_key=collection_key,
                    archive_index=archive_index,
                    url=url,
                    filename=filename,
                )
            )

    return RangeMapMetadata(
        version=version,
        ranges=ranges,
        archives=tuple(archives),
    )

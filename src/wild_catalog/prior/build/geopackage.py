from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyogrio
from pyproj import CRS, Transformer
from shapely import from_wkb
from shapely.ops import transform


@dataclass(frozen=True, slots=True)
class RangeGeometry:
    taxon_id: int
    geometry: Any


TAXON_ID_COLUMN_CANDIDATES = (
    "taxon_id",
    "taxonid",
    "taxonId",
    "taxonID",
    "inat_taxon_id",
    "iNaturalist taxon ID",
    "id",
)


def iter_range_geometries(gpkg_path: Path) -> Iterator[RangeGeometry]:
    """Yield taxon range geometries from an iNaturalist GeoPackage."""
    found_candidate_layer = False

    for layer_info in pyogrio.list_layers(gpkg_path):
        layer_name = str(layer_info[0])
        metadata, table = pyogrio.read_arrow(gpkg_path, layer=layer_name)

        if table.num_rows == 0:
            continue

        taxon_id_column = _find_taxon_id_column(table.column_names)

        if taxon_id_column is None:
            continue

        geometry_column = metadata.get("geometry_name")

        if geometry_column is None or geometry_column not in table.column_names:
            continue

        found_candidate_layer = True
        transformer = _build_transformer_to_epsg_4326(metadata.get("crs"))

        taxon_ids = table[taxon_id_column].to_pylist()
        geometries = table[str(geometry_column)].to_pylist()

        for taxon_id, geometry_wkb in zip(taxon_ids, geometries, strict=True):
            if taxon_id is None or geometry_wkb is None:
                continue

            geometry = from_wkb(geometry_wkb)

            if geometry is None or geometry.is_empty:
                continue

            if transformer is not None:
                geometry = transform(transformer.transform, geometry)

            yield RangeGeometry(
                taxon_id=int(taxon_id),
                geometry=geometry,
            )

    if not found_candidate_layer:
        raise ValueError(f"No layer with a recognized taxon ID column found in {gpkg_path}.")


def _find_taxon_id_column(columns: object) -> str | None:
    exact_column_names = {str(column): str(column) for column in columns}
    lowered_column_names = {str(column).lower(): str(column) for column in columns}

    for candidate in TAXON_ID_COLUMN_CANDIDATES:
        if candidate in exact_column_names:
            return exact_column_names[candidate]

        lowered_candidate = candidate.lower()
        if lowered_candidate in lowered_column_names:
            return lowered_column_names[lowered_candidate]

    return None


def _build_transformer_to_epsg_4326(crs: object) -> Transformer | None:
    if crs is None:
        return None

    source_crs = CRS.from_user_input(crs)

    if source_crs.to_epsg() == 4326:
        return None

    return Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)

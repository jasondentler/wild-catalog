[Architecture](./architecture.md)

# Species Range Prior Service

## Responsibility

The species range prior service generates localized, species-specific probability masks for a given geographic coordinate and active classifier class index. It translates location into a vector that can condition classifier outputs without changing the visual model itself.

## Technical Stack

* SQLite local range store compiled ahead of request time
* SQLite RTree bounding-box index for request-time candidate lookup
* Shapely point-in-geometry checks against stored WKB geometries
* Optional H3-keyed in-process cache for hot locations
* PyTorch tensor conversion for classifier-aligned prior masks
* [iNaturalist Open Range Map datasets](https://www.inaturalist.org/pages/range_maps) or another compatible offline range dataset
* Pyogrio, Shapely, and PyProj for pre-operational GeoPackage parsing and CRS handling

## Operation: `generate_prior_mask`

### Description

The service receives GPS coordinates and classifier class-index metadata. It
uses the coordinate to query an SQLite RTree for candidate species range
geometries, verifies exact point membership with Shapely, and returns a vector
`G` aligned exactly to the active classifier's class order.

Native, expected, or verified taxa are assigned `1.0`. Out-of-region taxa receive a configurable epsilon floor, such as `0.01`.

When GPS is missing, the service returns an all-ones mask. Missing GPS also treats `is_present` as `True` because there is no location evidence against the prediction.

### Inputs

* `gps_coordinates`: `(latitude, longitude)` tuple or `None`.
* `class_index`: Active classifier class-index metadata.

### Outputs

* `spatial_prior_mask`: 1D tensor/array of length `N`, where `N` equals the active classifier's class count.

## Classifier-aware interface

```python
class SpeciesRangePrior(Protocol):
    def generate_prior_mask(
        gps_coordinates: GpsCoordinates | None,
        class_index: ClassIndex,
    ) -> PriorMask:
        ...

    def get_presence_for_taxa(
        gps_coordinates: GpsCoordinates | None,
        taxon_ids: set[int],
    ) -> PresenceResult:
        ...
```

The prior service must not globally assume `inat21`. It may provide an `inat21` store as the first implementation, but compatibility must be explicit.

## SQLite range store

The request-time store answers two questions:

* Which candidate range geometries have bounding boxes that contain this point?
* Which candidate range geometries for a requested taxon set have bounding boxes
  that contain this point?

The initial schema is:

```sql
CREATE TABLE range_geometries (
    id INTEGER PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    min_lon REAL NOT NULL,
    min_lat REAL NOT NULL,
    max_lon REAL NOT NULL,
    max_lat REAL NOT NULL,
    geometry_wkb BLOB NOT NULL
);

CREATE VIRTUAL TABLE range_geometries_rtree USING rtree(
    id,
    min_lon,
    max_lon,
    min_lat,
    max_lat
);

CREATE INDEX idx_range_geometries_taxon_id
ON range_geometries (taxon_id);

CREATE TABLE range_store_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

The metadata table must include `source`, `source_version`, `geometry_format`,
and `built_at`. `geometry_format` is `wkb`. The service reads the configured
SQLite database from `WILD_CATALOG_RANGE_MAP_STORE_PATH`; when no path is
configured, it uses a stub store.

## Range Store Build Process

The request-time prior service reads from a local SQLite database.

The SQLite database is built by the Step 14A pre-operational builder from the
iNaturalist open range-map GeoPackage files. The builder discovers GeoPackage
archives from iNaturalist metadata, downloads missing archives into the local
range-map download directory in parallel, streams range geometries into a
temporary SQLite database as WKB rows, maintains an RTree from geometry bounds,
and atomically replaces the configured range store.

The build path uses `pyogrio.read_arrow()` to read GeoPackage layers without
adding GeoPandas, converts WKB geometries to Shapely objects, reprojects
non-EPSG:4326 geometries with PyProj, and writes Shapely geometries as WKB. The
confirmed iNaturalist GeoPackage schema includes a `taxon_id` field and a
`geom` geometry column. Optional SQLite `ATTACH` staging helpers are available
for workflows that need to copy GeoPackage feature layers into temporary SQLite
tables before normalization.

The pre-operational CLI logs task start and completion, parallel archive
download/reuse, archive processing, periodic geometry conversion progress,
SQLite writes, and validation. Long-running range-map builds should emit
progress at regular time intervals instead of running silently. Progress
messages include the SQLite database path, percent complete, processed counts,
and estimated time remaining based on elapsed work.

Archive download concurrency is configured with
`WILD_CATALOG_INAT_RANGE_MAPS_DOWNLOAD_CONCURRENCY` and defaults to `4`.

Range geometry rows are streamed into SQLite. The builder does not keep a global
in-memory set of cells or geometries, and it does not precompute H3 coverings.
H3 remains available only as a compact cache key for hot request-time
coordinates.

`/identify` must not download range maps, parse raw range-map archives, or write the SQLite range store.

## Performance notes

* Keep range maps local.
* Do not call external APIs during `/identify`.
* Do not download or parse range-map archives during `/identify`.
* Cache hot spatial cells.
* Keep prior vectors compact.
* Validate mask length against the active classifier metadata.

## Startup validation and version reporting

Startup should open and lightly validate the compiled SQLite range prior store. It should not rebuild range maps on every application startup.

Validation should confirm:

```text
range_geometries exists
range_geometries_rtree exists
range_store_metadata exists
required metadata keys are present
RTree row count is consistent with geometry row count
```

`GET /status` may report non-sensitive range-store metadata such as source, source version, geometry format, and build timestamp. Do not expose local filesystem paths.

If the configured range-map store is missing or invalid, startup should mark the range-prior task as failed with `local_data_unavailable`, and `/identify` should return `503` until the issue is resolved.

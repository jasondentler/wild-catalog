# Dependency Notes

## Species range prior

The request-time species range prior service reads compiled species range data
from a local SQLite database. The store keeps species range geometries as WKB
rows, uses an SQLite RTree for bounding-box candidate lookup, and verifies exact
point membership with Shapely. H3 is only used as an optional cache key for hot
locations.

The service depends on `wild_catalog.core.types.GpsCoordinates` and
`wild_catalog.classifier.types.ClassIndex` so its masks align with the active
classifier. It must not depend on API, taxonomy, pipeline, or concrete
classifier plugin modules.

Downloading, parsing, and compiling iNat21 open range maps is handled by the
Step 14A pre-operational builder. Archive downloads run in parallel according to
`WILD_CATALOG_INAT_RANGE_MAPS_DOWNLOAD_CONCURRENCY`; `/identify` must only read
the compiled SQLite store and must not download or parse range-map archives.

The Step 14A build path uses a narrow geospatial dependency set:

* `pyogrio` reads iNaturalist GeoPackage layers through Arrow without adding
  GeoPandas.
* `shapely` converts WKB geometry records into Polygon and MultiPolygon objects
  and performs request-time point membership checks.
* `pyproj` reprojects non-EPSG:4326 geometries before writing the compiled
  store.
* `h3` provides compact cache keys only; it is not used to precompute the
  primary range store.

`geopandas` is intentionally not included. Keep GeoPackage parsing in
`wild_catalog.prior.build.geopackage`. Keep request-time geometry logic in
`wild_catalog.prior.point_lookup` so `/identify` reads only the compiled SQLite
store and never parses raw range-map archives.

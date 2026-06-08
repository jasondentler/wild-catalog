# Dependency Notes

## Species range prior

The request-time species range prior service reads compiled species range data
from a local SQLite database. The store is keyed by H3 cell and taxon ID, and
the required `h3_resolution` value is read from `range_store_metadata`.

The service depends on `wild_catalog.core.types.GpsCoordinates` and
`wild_catalog.classifier.types.ClassIndex` so its masks align with the active
classifier. It must not depend on API, taxonomy, pipeline, or concrete
classifier plugin modules.

Downloading, parsing, and compiling iNat21 open range maps is deferred to Step
14A. `/identify` must only read the compiled SQLite store and must not download
or parse range-map archives.

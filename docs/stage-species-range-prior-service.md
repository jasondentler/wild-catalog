# Species Range Prior Service

The species range prior service generates localized, species-specific probability masks for a given GPS coordinate and active classifier class index. Effectively, when we know where a photo was taken, we can greatly improve accuracy by penalizing predictions for species that don't typically exist where the photo was taken. When we don't know where a photo was taken, this service does not affect the final prediction.

## Module Layout

The service implementation is split across a small set of focused modules under `src/wild_catalog/range_data/`:

* `species_range_prior_service.py`: orchestration, prior-mask generation, cache lookup, and point-in-polygon evaluation.
* `presence_cache.py`: H3-based cache key generation and the in-memory cache store.
* `class_index.py`: active classifier class-index metadata.
* `prior_mask.py`: the prior mask tensor container.
* `presence_result.py`: boolean presence results keyed by taxon ID.
* `species_range_store.py`: the range-store protocol.
* `sqlite_species_range_store.py`: SQLite-backed range-store implementation.

The package initializer re-exports these types from `wild_catalog.range_data` for convenience.

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

## Implementation Notes

* `PresenceCache` uses H3 cell keys derived from the input GPS coordinate and configured cache resolution.
* `SpeciesRangePriorService` keeps the point-in-geometry check local to the service and uses Shapely for exact membership tests after fetching candidates from the store.
* Production uses the SQLite-backed range store path from settings. The in-memory stub store lives under `tests/support/` and is reserved for unit tests and boundary tests that inject it explicitly.

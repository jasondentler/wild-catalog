[Architecture](./architecture.md)

# Species Range Prior Service

## Responsibility

The species range prior service generates localized, species-specific probability masks for a given geographic coordinate and active classifier class index. It translates location into a vector that can condition classifier outputs without changing the visual model itself.

## Technical Stack

* SQLite local range store compiled ahead of request time
* H3 spatial index for mapping GPS coordinates to range cells
* PyTorch tensor conversion for classifier-aligned prior masks
* [iNaturalist Open Range Map datasets](https://www.inaturalist.org/pages/range_maps) or another compatible offline range dataset
* H3 spatial index or GeoPandas-style spatial lookup


## Operation: `generate_prior_mask`

### Description

The service receives GPS coordinates and classifier class-index metadata. It maps the coordinates to an H3 cell, reads the local SQLite range store for taxa present in that cell, and returns a vector `G` aligned exactly to the active classifier's class order.

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

* Which taxon IDs are present in an H3 cell?
* Is a specific taxon ID present in an H3 cell?

The initial schema is:

```sql
CREATE TABLE range_cells (
    h3_cell TEXT NOT NULL,
    taxon_id INTEGER NOT NULL,
    PRIMARY KEY (h3_cell, taxon_id)
);
```

The metadata table must include `h3_resolution`. The service reads the configured SQLite database from `WILD_CATALOG_RANGE_MAP_STORE_PATH`; when no path is configured, it uses a stub store.

## Offline range-map compilation

Downloading and parsing iNaturalist open range maps is not part of the request-time service. Range databases are compiled ahead of request time in a later implementation stage.

`/identify` must not download range maps, parse raw range-map archives, or write the SQLite range store.

## Performance notes

* Keep range maps local.
* Do not call external APIs during `/identify`.
* Do not download or parse range-map archives during `/identify`.
* Cache hot spatial cells.
* Keep prior vectors compact.
* Validate mask length against the active classifier metadata.

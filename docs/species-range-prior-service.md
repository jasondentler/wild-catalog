[Architecture](./architecture.md)

# Species Range Prior Service

## Responsibility

The species range prior service generates localized, species-specific probability masks for a given geographic coordinate and active classifier class index. It translates location into a vector that can condition classifier outputs without changing the visual model itself.

## Technical Stack

* [iNaturalist Open Range Map datasets](https://www.inaturalist.org/pages/range_maps) or another compatible offline range dataset
* H3 spatial index or GeoPandas-style spatial lookup
* PyArrow / Parquet data store or SQLite
* NumPy or PyTorch tensor conversion

## Operation: `generate_prior_mask`

### Description

The service receives GPS coordinates and classifier class-index metadata. It maps the coordinates to a spatial cell, looks up which taxa are expected or verified in that cell, and returns a vector `G` aligned exactly to the active classifier's class order.

Native, expected, or verified taxa are assigned `1.0`. Out-of-region taxa receive a configurable epsilon floor, such as `0.01`.

When GPS is missing, range data is unavailable, or the active classifier's class index is unsupported, the service should return an all-ones mask unless configuration says to fail closed.

### Inputs

* `gps_coordinates`: `(latitude, longitude)` tuple or `None`.
* `class_index`: Active classifier class-index metadata.

### Outputs

* `spatial_prior_mask`: 1D tensor/array of length `N`, where `N` equals the active classifier's class count.

## Classifier-aware interface

```python
class SpeciesRangePrior(Protocol):
    def generate_prior_mask(
        self,
        gps_coordinates: tuple[float, float] | None,
        class_index: ClassIndex,
    ) -> PriorMask:
        ...
```

The prior service must not globally assume `inat21`. It may provide an `inat21` store as the first implementation, but compatibility must be explicit.

## Operation: `ensure_range_maps`

Downloads or verifies the configured offline range-map source and performs preprocessing into the local lookup format.

This should be an offline setup operation, not part of the hot `/identify` request path.

## Performance notes

* Keep range maps local.
* Do not call external APIs during `/identify`.
* Cache hot spatial cells.
* Keep prior vectors compact.
* Validate mask length against the active classifier metadata.

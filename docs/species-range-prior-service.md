[Architecture](./architecture.md)

# Species Range Prior Service
* **Responsibility**: Generates localized, species-specific probability distributions for any given geographic coordinate on Earth. It acts as an offline-compiled lookup registry that translates geometric coordinates into a mathematical filter mask.
* **Technical Stack**: [iNaturalist Open Range Map datasets](https://www.inaturalist.org/pages/range_maps), Uber H3 Spatial Index (or GeoPandas), PyArrow/Parquet data store.

## Operation: `generate_prior_mask`
* **Description**: Receives floating-point GPS coordinates and maps them to a specific spatial cell index (e.g., an H3 hexagon). It queries a pre-compiled dataset derived from the iNaturalist Open Range Map data to look up all $N$ target species classes mapped to that cell. Native species or verified populations within the cell are assigned a probability value of `1.0`. Out-of-region or non-native species are given a baseline epsilon penalty floor (e.g., `0.01`).
* **Inputs**:
  * `gps_coordinates` (Tuple of Floats): Physical telemetry location `(latitude, longitude)` extracted by the Image Conversion Service.
* **Outputs**:
  * `spatial_prior_mask` (1D Tensor/Array of length $N$): A geographic prior vector $G$ where indices match the species classification head mapping exactly.

## Operation `ensure_range_maps`
* **Description**: Downloads the range maps from [iNaturalist Open Range Map datasets](https://www.inaturalist.org/pages/range_maps) and performs any preprocessing necessary.

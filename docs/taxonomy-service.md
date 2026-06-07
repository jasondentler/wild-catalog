[Architecture](./architecture.md)

# Taxonomy Service

## Responsibility

The Taxonomy Service enriches classifier predictions with canonical scientific
taxonomy and localized common names.

It uses the iNaturalist Taxonomy DarwinCore Archive, `taxonomy.dwca.zip`, as the
local source of truth for taxon records, parent-child relationships, taxonomic
ranks, scientific names, and common names.

The service does **not** make live iNaturalist API calls during image
identification. The DarwinCore Archive is downloaded, parsed, and compiled into
local lookup tables ahead of request time so `/identify` responses remain fast,
predictable, and available offline.

## Source Dataset

The service uses the iNaturalist Taxonomy DarwinCore Archive:

```text
https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip
taxonomy.dwca.zip
```

This archive is expected to provide the taxonomic tree and common-name data used
to enrich model predictions.

## Why This Service Exists

Classifier models return machine-oriented class identifiers or logits. They do
not, by themselves, provide the full API response contract required by Wild
Catalog.

The API response requires each prediction to include:

* `confidence`
* `is_present`
* `taxonomy`
* `taxonomy_common_names`

The classifier is responsible for visual prediction. The Taxonomy Service is
responsible for turning classifier class IDs into user-facing taxonomic data.

Keeping this logic separate makes classifier models pluggable. A future
classifier can use a different class index as long as Wild Catalog can map that
classifier's class IDs to iNaturalist taxon IDs or another supported taxonomy
mapping.

## Responsibilities

The Taxonomy Service is responsible for:

1. Loading or compiling `taxonomy.dwca.zip`.
2. Mapping classifier class IDs to canonical taxon records.
3. Resolving the scientific lineage for each predicted taxon.
4. Resolving localized common names for each taxonomic rank.
5. Falling back gracefully when localized common names are unavailable.
6. Supporting taxonomy-drift handling between a model's training taxonomy and
   the current taxonomy dataset.
7. Returning enriched prediction payloads for the API response.

## Non-Responsibilities

The Taxonomy Service is **not** responsible for:

* Running image classification.
* Running object detection.
* Cropping images.
* Applying geographic priors to logits.
* Determining whether a species is present at a GPS coordinate.
* Calling the live iNaturalist API during `/identify`.

Species presence is owned by the Species Range Prior Service. The Taxonomy
Service may attach the final `is_present` value to enriched predictions, but it
should receive that value from the range/presence layer.

## `is_present`

The prediction response uses `is_present`, not `is_endemic`.

```json
{
  "confidence": 0.982,
  "is_present": true,
  "taxonomy": [
    "Animalia",
    "Chordata",
    "Aves",
    "Passeriformes",
    "Corvidae",
    "Cyanocitta",
    "Cyanocitta cristata"
  ],
  "taxonomy_common_names": [
    "Animals",
    "Chordates",
    "Birds",
    "Perching Birds",
    "Crows and Jays",
    "Blue Jays",
    "Blue Jay"
  ]
}
```

`is_present` means the predicted taxon is known, expected, or otherwise
geographically plausible for the provided location according to the Species
Range Prior Service.

This is intentionally broader and more accurate than `is_endemic`. A species can
be present in a location without being endemic to that location.

## Inputs

### Operation: `enrich_predictions`

#### Description

Enriches classifier predictions with scientific taxonomy and localized common
names.

#### Inputs

* `predictions`: A list of classifier prediction records.
  * Each prediction contains a classifier class ID and confidence score.
* `class_index`: Metadata for the active classifier's class index.
  * This allows the service to map classifier-specific class IDs to iNaturalist
    taxon IDs.
* `common_name_language`: A locale code for common-name lookup.
  * Example: `en-US`
  * Example: `es-MX`
* `presence_by_taxon_id`: A mapping from iNaturalist taxon ID to presence flag.
  * The Species Range Prior Service owns this data.
  * The Taxonomy Service attaches it to the final response as `is_present`.

## Outputs

The service returns enriched prediction records.

Each record contains:

* `confidence`: The classifier probability after logit conditioning.
* `is_present`: Whether the taxon is geographically present or plausible.
* `taxonomy`: Scientific names ordered from highest rank to lowest rank.
* `taxonomy_common_names`: Localized common names matching the same rank order as
  `taxonomy`.

## Suggested Internal Types

```python
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ClassPrediction:
    class_id: int
    confidence: float


@dataclass(frozen=True, slots=True)
class ClassIndex:
    id: str
    classifier_backend: str
    taxon_id_by_class_id: Mapping[int, int]


@dataclass(frozen=True, slots=True)
class TaxonRecord:
    taxon_id: int
    parent_taxon_id: int | None
    rank: str
    scientific_name: str
    accepted_taxon_id: int | None = None


@dataclass(frozen=True, slots=True)
class EnrichedPrediction:
    confidence: float
    is_present: bool
    taxonomy: tuple[str, ...]
    taxonomy_common_names: tuple[str, ...]


class TaxonomyService(Protocol):
    def enrich_predictions(
        self,
        predictions: Sequence[ClassPrediction],
        class_index: ClassIndex,
        common_name_language: str,
        presence_by_taxon_id: Mapping[int, bool],
    ) -> list[EnrichedPrediction]:
        ...
```

## Local Data Store

The DarwinCore Archive should be compiled into fast local lookup tables.

Recommended derived lookup structures:

```text
taxon_by_id
accepted_taxon_id_by_taxon_id
parent_taxon_id_by_taxon_id
children_by_parent_taxon_id
scientific_name_by_taxon_id
rank_by_taxon_id
common_names_by_taxon_id_and_locale
fallback_common_name_by_taxon_id
```

The exact physical format can evolve over time. Good initial options include:

* SQLite
* Parquet
* Arrow IPC
* compact JSON fixtures for tests

For production use, prefer a format that avoids parsing the full archive during
application startup.

## Common Name Resolution

Common-name lookup should follow this fallback order:

1. Requested locale exact match.
2. Requested language without region.
   * Example: `es-MX` falls back to `es`.
3. Project default locale.
   * Default: `en-US`
4. Any English common name.
5. Scientific name.

The service should never fail a prediction only because a localized common name
is unavailable.

## Taxonomy Lineage Resolution

For each predicted taxon:

1. Resolve the classifier class ID to a source taxon ID.
2. If the source taxon has an accepted replacement, resolve to the accepted taxon
   when appropriate.
3. Walk parent links from the resolved taxon up to the root.
4. Reverse the lineage so it is ordered from highest rank to lowest rank.
5. Return scientific names in that order.
6. Resolve common names for the same ordered lineage.

Example lineage order:

```text
Animalia
Chordata
Aves
Passeriformes
Corvidae
Cyanocitta
Cyanocitta cristata
```

The `taxonomy` and `taxonomy_common_names` arrays must have matching indexes.

## Taxonomy Drift

Classifier models are trained against fixed class indexes. Taxonomy changes over
time as taxa are renamed, split, lumped, or reclassified.

The Taxonomy Service should support explicit mapping between:

```text
classifier class ID
→ model training taxon ID
→ current accepted taxon ID
```

This allows Wild Catalog to keep model compatibility stable while returning
current taxonomy where a reliable mapping exists.

If no reliable drift mapping exists, the service should prefer a conservative
response using the model's original taxon mapping rather than inventing a newer
taxon assignment.

## Classifier Compatibility

Because classifier models are pluggable, the Taxonomy Service must not assume a
single fixed class index such as `inat21`.

Each classifier plugin must expose class-index metadata.

Example classifier metadata:

```python
@dataclass(frozen=True, slots=True)
class ClassifierMetadata:
    backend: str
    model_id: str
    class_count: int
    class_index_id: str
    output_type: str
    taxonomy_source: str
```

The Taxonomy Service should use `class_index_id` and the classifier-provided
class-index mapping to resolve class IDs correctly.

## Request-Time Behavior

During `/identify`, the Taxonomy Service should only perform local lookups.

It should not:

* download `taxonomy.dwca.zip`;
* parse the full DarwinCore Archive;
* call iNaturalist APIs;
* perform network requests;
* run slow migration or compilation work.

All expensive preparation should happen ahead of time through an explicit setup,
cache-building, or startup process.

## Operation: `ensure_taxonomy`

### Description

Downloads or verifies `taxonomy.dwca.zip` and compiles it into the local lookup
store used by request-time enrichment.

This operation is not part of the hot `/identify` request path.

### Inputs

* Optional configured archive URL.
* Optional local archive path.
* Optional local compiled taxonomy store path.

### Outputs

* A compiled local taxonomy store.
* Metadata describing the source archive version or build time.

### Failure Behavior

If taxonomy setup fails, the application should fail clearly during setup or
readiness checks.

The lightweight `/health` endpoint should not perform taxonomy validation. A
future readiness endpoint may validate that taxonomy data is available.

## Configuration

Recommended environment variables:

```text
WILD_CATALOG_TAXONOMY_DWCA_URL=https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip
WILD_CATALOG_TAXONOMY_DWCA_PATH=
WILD_CATALOG_TAXONOMY_STORE_PATH=data/taxonomy
WILD_CATALOG_TAXONOMY_DEFAULT_LANGUAGE=en-US
WILD_CATALOG_TAXONOMY_ENABLE_DRIFT_MAPPING=true
```

The exact archive URL should be verified against the current iNaturalist
developer documentation before automation is implemented.

## Performance Requirements

The Taxonomy Service is on the `/identify` hot path, so enrichment must be fast.

Guidelines:

* Load compact lookup indexes once per process.
* Do not parse zip files during image identification.
* Cache common lineage lookups.
* Cache common-name lookups by `(taxon_id, language)`.
* Avoid repeated parent-chain traversal for common taxa.
* Keep request-time work proportional to the number of top-k predictions, not
  the total number of taxa.

## Memory Requirements

The service should avoid keeping unnecessary copies of the full DarwinCore
Archive in memory.

Guidelines:

* Compile raw archive data into compact lookup tables.
* Use immutable or read-only stores where practical.
* Load only the lookup structures required for enrichment.
* Use fixtures for tests instead of the full archive.
* Do not duplicate taxonomy stores per request.

## Testing

Default tests should use small local fixtures instead of the full iNaturalist
archive.

Recommended tests:

* Class ID maps to expected taxon ID.
* Taxon ID resolves to expected scientific lineage.
* Common names resolve for `en-US`.
* Requested locale falls back to language-only locale.
* Missing localized common name falls back to English.
* Missing common name falls back to scientific name.
* `taxonomy` and `taxonomy_common_names` arrays have the same length.
* Taxonomy drift mapping resolves accepted taxon IDs correctly.
* Unknown class ID returns a controlled error.
* `is_present` is attached from `presence_by_taxon_id`.
* Request-time enrichment does not perform network calls.

Integration tests using the full DarwinCore Archive should be opt-in because the
archive is large and may require download/setup time.

## API Response Integration

The API response prediction object should use this shape:

```json
{
  "confidence": 0.982,
  "is_present": true,
  "taxonomy": [
    "Animalia",
    "Chordata",
    "Aves",
    "Passeriformes",
    "Corvidae",
    "Cyanocitta",
    "Cyanocitta cristata"
  ],
  "taxonomy_common_names": [
    "Animals",
    "Chordates",
    "Birds",
    "Perching Birds",
    "Crows and Jays",
    "Blue Jays",
    "Blue Jay"
  ]
}
```

## Implementation Notes

The first implementation should be intentionally simple:

1. Add a `TaxonomyService` protocol.
2. Add a `StubTaxonomyService` for tests.
3. Add a local fixture-backed taxonomy store.
4. Add iNaturalist DarwinCore Archive parsing as an offline setup step.
5. Add a compiled local lookup format.
6. Add request-time enrichment against the compiled local store.
7. Add classifier class-index compatibility checks.
8. Add localization fallback behavior.
9. Add taxonomy drift mapping only after the basic lookup flow is stable.

## Summary

The Taxonomy Service is necessary because the API response exposes scientific
taxonomy and localized common names, while classifier plugins only produce class
scores.

It should remain an in-process enrichment layer backed by local compiled data
from the iNaturalist Taxonomy DarwinCore Archive. It should not be a live network
service, and it should not perform expensive archive parsing during `/identify`.
```
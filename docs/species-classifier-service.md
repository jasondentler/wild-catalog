[Architecture](./architecture.md)

# Species Classifier Service

## Responsibility

The species classifier service computes fine-grained taxonomic predictions for cropped organism images. Classifier models are pluggable because species-identification models are expected to improve over time.

The preferred classifier output is raw logits, not final probabilities. Raw logits allow the logit conditioning layer to apply geographic priors before Softmax.

## Plugin design

The core pipeline depends on a `SpeciesClassifier` protocol rather than a concrete model implementation.

```python
class SpeciesClassifier(Protocol):
    @property
    def metadata(self) -> ClassifierMetadata:
        ...

    def predict_species(self, cropped_images: Sequence[Image.Image]) -> RawClassifierOutput:
        ...
```

## Classifier metadata

Classifier metadata is required because the range prior service, taxonomy service, and logit conditioning layer must know how class indices map to taxa.

```python
@dataclass(frozen=True, slots=True)
class ClassifierMetadata:
    backend: str
    model_id: str
    class_count: int
    class_index_id: str
    output_type: Literal["logits", "probabilities"]
    taxonomy_source: str
```

## Classifier output

```python
@dataclass(frozen=True, slots=True)
class RawClassifierOutput:
    logits: torch.Tensor
    class_index: ClassIndex
```

The classifier metadata `output_type` should be `"logits"` for logit conditioning. Classifiers that can only return probabilities may be supported later, but geographic conditioning will be less principled unless the adapter can expose logits.

## Default planned production plugin: Birder iNat21

The default planned classifier plugin is a Birder/iNaturalist 2021-compatible adapter.

Expected behavior:

* Load the configured model once per process.
* Move the model to the shared PyTorch device helper result.
* Use `.eval()`.
* Use `torch.inference_mode()`.
* Transform RGB crops according to the model's required input size and normalization.
* Batch crops for inference.
* Return raw, unconditioned logits.
* Expose a stable `class_index_id`, such as `inat21`.

## Stub implementation

`StubSpeciesClassifier` should remain the default for fast unit tests and API contract tests. It emits deterministic fixture logits and class-index metadata without requiring model weights, Birder, or GPU/MPS availability.

## Configuration

```text
WILD_CATALOG_CLASSIFIER_BACKEND=birder-inat21
WILD_CATALOG_SPECIES_CLASSIFIER_MODEL_CACHE_PATH=
WILD_CATALOG_SPECIES_CLASSIFIER_BATCH_SIZE=8
WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K=12
```

## Registry

```python
def build_classifier(settings: Settings) -> SpeciesClassifier:
    if settings.classifier_backend == "stub":
        return StubSpeciesClassifier()

    if settings.classifier_backend == "birder-inat21":
        from wild_catalog.classifier.birder import BirderSpeciesClassifier

        return BirderSpeciesClassifier(settings)

    raise ValueError(f"Unknown classifier backend: {settings.classifier_backend}")
```

Unknown classifier backend names should fail at startup with a clear configuration error.

## Class-index compatibility

The classifier's class index is part of the service contract. The range prior and taxonomy services must not assume a global hard-coded class ordering. They must use the active classifier's `class_index_id` and class-index metadata.

If no compatible range prior is available for a classifier, the prior service should return an all-ones mask rather than inventing an incompatible mapping.

If no compatible taxonomy store is available, the taxonomy service should fail clearly or use an explicitly configured fallback.

## Testing

Default tests use `StubSpeciesClassifier` and do not require model weights. Real-model integration tests are skipped unless explicitly enabled with:

```text
make test
```

Shared classifier contract tests should verify:

* One output row per crop.
* `class_count` matches score tensor width.
* `class_index_id` is present.
* Output can feed the logit conditioning layer.
* Empty crop lists are handled predictably.

## Real Model Integration Tests

Real Birder classifier tests live under:

```text
tests/integration/classifier/
```

They use realistic project fixtures from:

```text
sample-images/
```

Run the fast unit suite with:

```bash
make test-fast
```

Run the full suite, including real Birder integration tests, with:

```bash
make test
```

Run the repository PR gate with:

```bash
make pr
```

These tests verify the adapter contract for `hieradet_d_small_dino-v2-inat21`: model loading, RGB transforms, batching, raw logits, class-index metadata, and output shape. They are not general model-evaluation tests.

## Concrete Birder iNat21 implementation requirements

The Birder/iNaturalist 2021 adapter should be implemented as the default real classifier backend behind the `SpeciesClassifier` protocol.

The adapter must:

1. Load the configured model once per process.
2. Use the shared torch device helper.
3. Move the model to the selected device.
4. Use `.eval()` and `torch.inference_mode()`.
5. Transform RGB crops according to the model's requirements.
6. Batch crops according to `WILD_CATALOG_SPECIES_CLASSIFIER_BATCH_SIZE`.
7. Return raw logits, not probabilities.
8. Expose a stable `ClassIndex` mapping classifier class IDs to iNaturalist taxon IDs.
9. Expose `warmup()` for startup pre-warming.

Class-index compatibility is a core contract. Tests should prove that classifier class IDs map to taxon IDs present in the taxonomy store and that the prior mask length matches the classifier output width.

The curated integration test for `sample-images/20260402-IMG_7906.jpg` should verify the classifier/prior/conditioning/taxonomy chain identifies Neotropic Cormorant / `Nannopterum brasilianum`.

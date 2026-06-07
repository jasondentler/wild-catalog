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

    def predict_species(self, cropped_images: Sequence[Image.Image]) -> ClassifierOutput:
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
class ClassifierOutput:
    scores: torch.Tensor
    class_index: ClassIndex
    output_type: Literal["logits", "probabilities"]
```

For logit conditioning, `output_type` should be `"logits"`. Classifiers that can only return probabilities may be supported later, but geographic conditioning will be less principled unless the adapter can expose logits.

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
CLASSIFIER_REGISTRY: dict[str, ClassifierFactory] = {
    "stub": build_stub_classifier,
    "birder-inat21": build_birder_inat21_classifier,
}
```

Unknown classifier backend names should fail at startup with a clear configuration error.

## Class-index compatibility

The classifier's class index is part of the service contract. The range prior and taxonomy services must not assume a global hard-coded class ordering. They must use the active classifier's `class_index_id` and class-index metadata.

If no compatible range prior is available for a classifier, the prior service should return an all-ones mask rather than inventing an incompatible mapping.

If no compatible taxonomy store is available, the taxonomy service should fail clearly or use an explicitly configured fallback.

## Testing

Default tests use `StubSpeciesClassifier` and do not require model weights. Real-model integration tests are skipped unless explicitly enabled with:

```text
WILD_CATALOG_RUN_REAL_MODEL_TESTS=1
```

Shared classifier contract tests should verify:

* One output row per crop.
* `class_count` matches score tensor width.
* `class_index_id` is present.
* Output can feed the logit conditioning layer.
* Empty crop lists are handled predictably.

# Wild Catalog Implementation Plan

This plan prioritizes maintainability, readability, low memory usage, and warm-path API response times under 500ms where practical. It incorporates the current architectural decisions:

* `ultralytics` is not used.
* `pillow-heif` is not used.
* Detector models are pluggable.
* Classifier models are pluggable.
* The default planned detector is Grounding DINO with an organism-focused prompt.

## 1. Define the performance target

Target warm-path behavior:

* `GET /health`: under 500ms.
* `GET /openapi.json`: under 500ms.
* `POST /identify` with stub plugins: under 500ms.
* `POST /identify` with real models: under 500ms when models are already loaded, input size is bounded, detections are capped, and crop images are not returned.

Explicitly outside the strict warm-path target:

* First model download.
* First model load.
* Very large RAW conversion.
* Multipart responses containing many crop images.

## 2. Establish the package structure

Recommended structure:

```text
src/wild_catalog/
  api/
    app.py
    dependencies.py
    errors.py
    request_models.py
    response_models.py
    multipart.py
    content_negotiation.py

  core/
    config.py
    device.py
    timing.py
    types.py

  conversion/
    service.py
    exif.py
    raw.py
    standard.py
    platform_conversion/
      protocols.py
      macos_sips.py
      imagemagick.py
      linux_heif_convert.py
      windows_wic.py
      noop.py

  detection/
    protocols.py
    registry.py
    types.py
    stub.py
    grounding_dino.py
    prompt.py
    postprocess.py

  deduplication/
    service.py
    iou.py

  cropping/
    service.py

  classifier/
    protocols.py
    registry.py
    types.py
    stub.py
    birder_inat21.py
    transforms.py

  prior/
    service.py
    store.py
    h3_index.py
    stub.py

  conditioning/
    service.py

  taxonomy/
    service.py
    store.py
    stub.py

  pipeline/
    identify.py
    models.py

  data/
    class_index.py
```

Keep service logic independent of FastAPI. FastAPI should call the pipeline; it should not contain the pipeline.

## 3. Implement shared domain types

Create explicit immutable types for boxes, detections, crops, classifier outputs, prior masks, and predictions.

Recommended examples:

```python
@dataclass(frozen=True, slots=True)
class BoundingBox:
    xmin: int
    ymin: int
    xmax: int
    ymax: int
```

```python
@dataclass(frozen=True, slots=True)
class Detection:
    bounding_box: BoundingBox
    confidence: float
    label: str
    category: DetectionCategory
    source: str
```

Use frozen dataclasses with `slots=True` for internal pipeline objects to keep memory lower and behavior easier to reason about.

## 4. Implement configuration

Create `core/config.py`.

Recommended variables:

```text
WILD_CATALOG_ENV=development
WILD_CATALOG_MAX_UPLOAD_BYTES=26214400
WILD_CATALOG_MAX_IMAGE_PIXELS=24000000
WILD_CATALOG_MAX_DETECTIONS=8
WILD_CATALOG_CROP_MARGIN_RATIO=0.12
WILD_CATALOG_MAX_CONCURRENT_IDENTIFY_REQUESTS=1

WILD_CATALOG_DETECTOR_BACKEND=grounding-dino
WILD_CATALOG_DETECTOR_MODEL_CACHE_PATH=
WILD_CATALOG_GROUNDING_DINO_MODEL_ID=
WILD_CATALOG_GROUNDING_DINO_PROMPT=
WILD_CATALOG_GROUNDING_DINO_BOX_THRESHOLD=0.25
WILD_CATALOG_GROUNDING_DINO_TEXT_THRESHOLD=0.25

WILD_CATALOG_CLASSIFIER_BACKEND=birder-inat21
WILD_CATALOG_SPECIES_CLASSIFIER_MODEL_CACHE_PATH=
WILD_CATALOG_SPECIES_CLASSIFIER_BATCH_SIZE=8
WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K=12

WILD_CATALOG_ENABLE_PLATFORM_IMAGE_CONVERSION=true
WILD_CATALOG_PLATFORM_IMAGE_CONVERTER=auto
WILD_CATALOG_PLATFORM_CONVERSION_TIMEOUT_SECONDS=10
WILD_CATALOG_SIPS_PATH=/usr/bin/sips
WILD_CATALOG_IMAGEMAGICK_PATH=magick
WILD_CATALOG_HEIF_CONVERT_PATH=heif-convert

WILD_CATALOG_RANGE_MAP_PATH=
WILD_CATALOG_PRIOR_EPSILON=0.01
WILD_CATALOG_PRIOR_GAMMA=1.0
WILD_CATALOG_PRELOAD_MODELS=false
```

## 5. Implement device selection

Create one shared device helper:

1. Prefer Apple Silicon MPS when available and not inside Docker.
2. Else prefer CUDA.
3. Else use CPU.
4. Cache the result.

Detector and classifier plugins should both use this helper.

## 6. Implement API skeleton

Build:

* `GET /health`
* `GET /openapi.json`
* `POST /identify`

Start with stub detector and classifier plugins. The first working milestone should prove the API contract without real model downloads.

## 7. Implement request and response models

Create Pydantic models for:

* `IdentifyRequest`
* `ExifOverride`
* `BoundingBoxResponse`
* `PredictionResponse`
* `DetectionResponse`

The public response should remain stable even when detector or classifier plugins change.

## 8. Implement image conversion

Implement direct support for:

* JPEG / JPG
* PNG
* WebP
* supported RAW formats through `rawpy`

Rules:

1. Do not add `pillow-heif`.
2. Do not use `shell=True`.
3. Use temp directories.
4. Apply subprocess timeouts.
5. Enforce upload and pixel limits.
6. Return helpful unsupported-format errors when conversion is unavailable.

## 9. Implement pluggable detection framework

Define:

```python
class ObjectDetector(Protocol):
    @property
    def metadata(self) -> DetectorMetadata:
        ...

    def locate_objects(self, image: Image.Image) -> list[Detection]:
        ...
```

Add registry:

```python
DETECTOR_REGISTRY = {
    "stub": build_stub_detector,
    "grounding-dino": build_grounding_dino_detector,
}
```

Unknown backends should fail at startup with clear errors.

## 10. Implement Grounding DINO detector plugin

The default prompt:

```text
bird . mammal . animal . reptile . amphibian . fish .
insect . butterfly . moth . beetle . dragonfly . spider . snail .
flower . plant . tree . leaf . grass . moss . lichen .
mushroom . fungus .
```

Responsibilities:

1. Own prompt configuration.
2. Preprocess the image for the model.
3. Run inference under `torch.inference_mode()`.
4. Postprocess model boxes into pixel `xyxy` coordinates.
5. Normalize returned labels into detection categories.
6. Return stable `Detection` objects.

## 11. Implement deduplication

Deduplicate by normalized detection category rather than exact raw label.

Default policy:

1. Group by category.
2. Sort by confidence descending.
3. Compute IoU.
4. Remove overlaps above threshold.
5. Prefer specificity when confidence is close.

## 12. Implement cropping

Crop after deduplication only. Apply margins, clamp to image bounds, and return RGB crops. Do not encode crops unless the request asks for detected images.

## 13. Implement pluggable classifier framework

Define:

```python
class SpeciesClassifier(Protocol):
    @property
    def metadata(self) -> ClassifierMetadata:
        ...

    def predict_species(self, cropped_images: Sequence[Image.Image]) -> ClassifierOutput:
        ...
```

Add registry:

```python
CLASSIFIER_REGISTRY = {
    "stub": build_stub_classifier,
    "birder-inat21": build_birder_inat21_classifier,
}
```

Classifier metadata must expose class-index identity and class count.

## 14. Implement Birder iNat21 classifier plugin

Responsibilities:

1. Load the configured model once.
2. Use the shared device helper.
3. Use `.eval()` and `torch.inference_mode()`.
4. Batch crops.
5. Return raw logits.
6. Expose `class_index_id`, such as `inat21`.

Default tests should use `StubSpeciesClassifier`. Real-model tests should run only with `WILD_CATALOG_RUN_REAL_MODEL_TESTS=1`.

## 15. Implement classifier-aware range priors

The prior service must accept the active classifier class index. It must not assume all future classifiers use iNaturalist 2021 ordering.

Behavior:

* GPS missing: return all-ones mask.
* Compatible prior data available: return location-aware prior mask.
* Compatible prior data unavailable: return all-ones mask or fail clearly depending on configuration.

## 16. Implement logit conditioning

Use:

```text
z_conditioned = z_raw + gamma * log(G + epsilon)
```

Then apply Softmax and extract top-k predictions.

Validate shape compatibility before computation.

## 17. Implement taxonomy enrichment

Taxonomy lookup should use the active classifier class index. It should return:

* scientific lineage;
* localized common-name lineage;
* is_present flag when GPS/range data supports it.

## 18. Implement pipeline orchestration

The `IdentifyPipeline` should receive already-built services and plugins.

Pipeline flow:

1. Validate request.
2. Convert image and extract metadata.
3. Apply metadata overrides.
4. Detect candidate subjects.
5. Deduplicate detections.
6. Cap detections.
7. Crop targets.
8. Classify crops.
9. Generate classifier-aware range prior.
10. Apply logit conditioning.
11. Enrich taxonomy/common names.
12. Build response.
13. Optionally attach crop images for multipart output.

The pipeline should not import Grounding DINO, Birder, or platform converter modules directly.

## 19. Implement content negotiation

Behavior:

* `return_detected_images=true`: force `multipart/mixed`.
* `return_detected_images=false` and `Accept: application/json`: JSON only.
* `return_detected_images=false` and `Accept: multipart/mixed`: multipart with JSON part only.

Avoid base64. Use binary image parts for returned crops.

## 20. Implement error handling

Map errors clearly:

* `400`: malformed request.
* `413`: upload or decoded image too large.
* `415`: unsupported media type or unavailable converter.
* `422`: conversion/decode failure for a nominally supported format.
* `503`: model or data store unavailable.
* `500`: unexpected failure.

## 21. Add startup pre-warming

Production deployments can set:

```text
WILD_CATALOG_PRELOAD_MODELS=true
```

Startup should optionally load detector, classifier, taxonomy, and range-prior data. This avoids first-request latency spikes.

## 22. Add bounded concurrency

Use a semaphore around expensive identify operations.

Start with:

```text
WILD_CATALOG_MAX_CONCURRENT_IDENTIFY_REQUESTS=1
```

Increase only after measuring memory and p95 latency.

## 23. Add timing instrumentation

Log:

* conversion time;
* detection time;
* deduplication time;
* cropping time;
* classification time;
* prior time;
* conditioning time;
* taxonomy time;
* serialization time;
* total time.

Do not expose timings publicly by default.

## 24. Test strategy

Unit tests:

* API request validation.
* Format sniffing.
* Platform converter selection.
* Detector registry.
* Grounding DINO postprocessing with mocked outputs.
* Label normalization.
* Deduplication IoU and specificity behavior.
* Crop clamping.
* Classifier registry.
* Stub classifier contract.
* Prior mask compatibility.
* Logit conditioning math.
* Taxonomy fallback.
* Multipart response formatting.

Integration tests:

* Real detector plugin with opt-in flag.
* Real classifier plugin with opt-in flag.
* End-to-end fixture image.
* Platform conversion adapters mocked by default, real only in platform-specific environments.

Performance tests:

* Stub `/identify` p95 under 500ms.
* Warm real-model benchmark reported separately.

## 25. Milestones

### Milestone 1: API contract with stubs

* FastAPI app.
* Request/response models.
* Stub detector.
* Stub classifier.
* JSON and multipart response tests.

### Milestone 2: Image conversion and platform adapters

* JPEG/PNG/WebP support.
* RAW support.
* EXIF extraction.
* Clear unsupported-format behavior.

### Milestone 3: Detector plugin framework

* Detector protocol.
* Detector registry.
* Detection domain types.
* Grounding DINO plugin.
* Label normalization.
* Detector contract tests.

### Milestone 4: Deduplication and cropping

* Category-aware IoU deduplication.
* Specificity tie-breaker.
* Margin-aware crop extraction.
* Memory guardrails.

### Milestone 5: Classifier plugin framework

* Classifier protocol.
* Classifier registry.
* Classifier metadata.
* Stub classifier.
* Birder iNat21 plugin.

### Milestone 6: Priors, conditioning, and taxonomy

* Classifier-aware range prior.
* Logit conditioning.
* Taxonomy/common-name enrichment.
* is_present flag behavior.

### Milestone 7: Production hardening

* Pre-warming.
* Bounded concurrency.
* Stage timing.
* Error handling.
* Performance benchmarks.
* Documentation updates.

## 26. Final implementation priority

Build in this order:

1. API and stubs.
2. Image conversion.
3. Platform conversion adapter interface.
4. Detector plugin framework.
5. Grounding DINO detector plugin.
6. Deduplication and cropping.
7. Classifier plugin framework.
8. Birder iNat21 classifier plugin.
9. Classifier-aware range priors.
10. Logit conditioning.
11. Taxonomy enrichment.
12. Multipart responses.
13. Pre-warming, concurrency, and performance tests.

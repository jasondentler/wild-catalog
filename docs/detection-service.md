[Architecture](./architecture.md)

# Detection Service

## Responsibility

The detection service locates candidate living subjects inside the image so downstream services can crop and classify them. It should answer only this question:

> Where are the likely organisms or organism-like subjects worth cropping?

It should not produce final species identity. Final biological identification belongs to the classifier, range-prior, logit-conditioning, and taxonomy services.

## Plugin design

Detector models are pluggable. The core pipeline depends on the `ObjectDetector` protocol rather than a concrete model implementation.

```python
class ObjectDetector(Protocol):
    @property
    def metadata(self) -> DetectorMetadata:
        ...

    def locate_objects(self, image: Image.Image) -> list[Detection]:
        ...
```

### Stable internal output

```python
@dataclass(frozen=True, slots=True)
class Detection:
    bounding_box: BoundingBox
    confidence: float
    label: str
    category: DetectionCategory
    source: str
```

```python
@dataclass(frozen=True, slots=True)
class BoundingBox:
    xmin: int
    ymin: int
    xmax: int
    ymax: int
```

Coordinates are always `xyxy` pixel coordinates in the normalized image's coordinate space.

### Metadata

```python
@dataclass(frozen=True, slots=True)
class DetectorMetadata:
    backend: str
    model_id: str
    supports_text_prompt: bool
    detection_categories: frozenset[DetectionCategory]
    coordinate_format: str = "xyxy_pixels"
```

## Default planned production plugin: Grounding DINO

The default planned detector plugin is a Grounding DINO-compatible open-vocabulary detector.

### Default prompt

```text
bird . mammal . animal . reptile . amphibian . fish .
insect . butterfly . moth . beetle . dragonfly . spider . snail .
flower . plant . tree . leaf . grass . moss . lichen .
mushroom . fungus .
```

The prompt should be owned by the Grounding DINO plugin, not the pipeline.

## Explicitly excluded detector dependency

Wild Catalog should not use `ultralytics` as a runtime dependency.

The former YOLO/COCO detection design has been replaced by a pluggable detector interface. A future YOLO-like model may still be added if its license and dependency chain are acceptable, but it must be implemented as a detector plugin behind the same protocol.

## Label normalization

Open-vocabulary detectors may return labels such as `bird`, `animal`, `flower`, `plant`, `mushroom`, or `fungus`. The detector plugin should normalize model-specific labels into broad internal categories.

Recommended categories:

```python
class DetectionCategory(StrEnum):
    ANIMAL = "animal"
    PLANT = "plant"
    FUNGUS = "fungus"
    LICHEN = "lichen"
    UNKNOWN = "unknown"
```

Recommended normalization map:

```python
DETECTION_CATEGORY_BY_LABEL = {
    "bird": "animal",
    "mammal": "animal",
    "animal": "animal",
    "reptile": "animal",
    "amphibian": "animal",
    "fish": "animal",
    "insect": "animal",
    "butterfly": "animal",
    "moth": "animal",
    "beetle": "animal",
    "dragonfly": "animal",
    "spider": "animal",
    "snail": "animal",

    "flower": "plant",
    "plant": "plant",
    "tree": "plant",
    "leaf": "plant",
    "grass": "plant",
    "moss": "plant",

    "lichen": "lichen",
    "mushroom": "fungus",
    "fungus": "fungus",
}
```

Unknown labels should be discarded unless a plugin explicitly maps them to a supported category.

## Configuration

```text
WILD_CATALOG_DETECTOR_BACKEND=grounding-dino
WILD_CATALOG_DETECTOR_MODEL_CACHE_PATH=
WILD_CATALOG_GROUNDING_DINO_MODEL_ID=
WILD_CATALOG_GROUNDING_DINO_PROMPT=
WILD_CATALOG_GROUNDING_DINO_BOX_THRESHOLD=0.25
WILD_CATALOG_GROUNDING_DINO_TEXT_THRESHOLD=0.25
WILD_CATALOG_MAX_DETECTIONS=8
```

## Registry

Use a small registry to avoid hard-coded model selection inside the pipeline.

```python
DETECTOR_REGISTRY: dict[str, DetectorFactory] = {
    "stub": build_stub_detector,
    "grounding-dino": build_grounding_dino_detector,
}
```

Unknown detector backend names should fail at startup with a clear configuration error.

## Testing

Every detector plugin should pass shared contract tests:

* Returns pixel `xyxy` boxes.
* Returns boxes inside image boundaries.
* Returns normalized categories.
* Does not intentionally detect people.
* Handles no-detection images.
* Respects `WILD_CATALOG_MAX_DETECTIONS`.

Grounding DINO-specific tests should mock model outputs in default CI and reserve real-model tests for opt-in integration test runs.

## Concrete Grounding DINO implementation requirements

The Grounding DINO detector plugin should be implemented as the default real detector backend behind the `ObjectDetector` protocol.

Required files:

```text
src/wild_catalog/detection/grounding_dino.py
src/wild_catalog/detection/grounding_dino_prompt.py
src/wild_catalog/detection/grounding_dino_postprocess.py
```

The plugin must:

1. Load the configured model once per process.
2. Use the shared torch device helper.
3. Run the configured organism prompt.
4. Convert model boxes to `xyxy` pixel boxes.
5. Clamp boxes to image bounds.
6. Drop invalid boxes.
7. Normalize labels into supported detection categories.
8. Filter by configured box/text thresholds.
9. Return `Detection` objects sorted by confidence.
10. Expose `warmup()` for startup pre-warming.

The detector must not classify species, call taxonomy services, apply geographic priors, crop images, or import API modules.

Missing or unloadable model weights should fail startup readiness with a controlled `model_unavailable`/`503` path and should be visible through `GET /status`.

# Wild Catalog Implementation Plan

## Goal

Implement Wild Catalog as a maintainable, readable, low-memory image identification
API for nature photos.

The system should identify animals, plants, fungi, lichens, and other natural
subjects in uploaded photographs, return species-level predictions where
possible, enrich those predictions with taxonomy and localized common names, and
optionally return cropped detection images.

The implementation should prioritize:

1. Maintainability.
2. Readability.
3. Low memory usage.
4. Stable API contracts.
5. Pluggable detector and classifier models.
6. Warm-path API response times under 500ms where practical.

The 500ms target applies to normal warm requests with models and lookup data
already loaded. It does not apply to first-time model downloads, cold model
initialization, taxonomy archive compilation, range-map preprocessing, very large
RAW files, or platform image conversion failures.

---

## 1. Establish the package layout

Use the existing `src/` package layout.

Recommended structure:

```text
src/
  wild_catalog/
    __init__.py

    api/
      __init__.py
      app.py
      dependencies.py
      errors.py
      request_models.py
      response_models.py
      status_models.py
      status_serializers.py
      readiness.py
      multipart.py
      content_negotiation.py
      status_models.py
      status_serializers.py
      readiness.py

    core/
      __init__.py
      config.py
      device.py
      timing.py
      errors.py
      types.py

    conversion/
      __init__.py
      service.py
      exif.py
      raw.py
      standard.py
      format_sniffing.py
      platform_conversion/
        __init__.py
        protocols.py
        registry.py
        noop.py
        macos_sips.py
        linux_imagemagick.py
        windows_imagemagick.py
        windows_wic.py

    detection/
      __init__.py
      protocols.py
      registry.py
      types.py
      policy.py
      stub.py
      grounding_dino.py
      grounding_dino_prompt.py
      grounding_dino_postprocess.py

    deduplication/
      __init__.py
      service.py
      iou.py

    cropping/
      __init__.py
      service.py
      types.py

    classifier/
      __init__.py
      protocols.py
      registry.py
      types.py
      stub.py
      birder.py
      transforms.py

    prior/
      __init__.py
      protocols.py
      service.py
      store.py
      h3_index.py
      stub.py
      types.py

    conditioning/
      __init__.py
      service.py

    taxonomy/
      __init__.py
      protocols.py
      service.py
      store.py
      dwca.py
      stub.py
      types.py

    pipeline/
      __init__.py
      identify.py
      models.py

    startup/
      __init__.py
      status.py
      tasks.py
      warmup.py

    startup/
      __init__.py
      status.py
      tasks.py
      warmup.py

    data/
      __init__.py
      class_index.py

tests/
  unit/
    api/
    conversion/
    detection/
    deduplication/
    cropping/
    classifier/
    prior/
    conditioning/
    taxonomy/
    pipeline/
    architecture/
  integration/
    conversion/
    detection/
    classifier/
    taxonomy/
    pipeline/
```

Keep the API layer thin. The API gateway should parse HTTP requests, call the
pipeline, and serialize responses. It should not contain model, cropping, EXIF,
taxonomy, or range-prior logic.

---

## 2. Define dependency direction

Use this dependency direction:

```text
api
→ pipeline
→ service protocols
→ service implementations
→ core
```

`core` is the lowest-level package. It must not import from any Wild Catalog
feature package.

The API package owns HTTP, FastAPI, Pydantic request models, response models, and
multipart serialization.

The pipeline package owns orchestration. It depends on service protocols, not
specific model implementations.

Detection and classifier packages own model plugin protocols, registries, stubs,
and concrete adapters.

Service packages must not import from `wild_catalog.api`.

Model-specific plugins must not leak into the API or pipeline.

Add tests in `tests/unit/architecture/test_import_boundaries.py` to enforce
these rules.

---

## 3. Implement shared domain types

Create explicit immutable types for boxes, detections, crops, classifier outputs,
prior masks, taxonomy records, and predictions.

These types should live close to the part of the system that owns them. Avoid a
single giant `types.py` file that becomes a dumping ground. Shared types that are
used across several pipeline stages belong in `src/wild_catalog/core/types.py`.
Plugin-specific types belong inside their plugin area.

Recommended layout:

```text
src/wild_catalog/
  core/
    types.py

  detection/
    types.py

  cropping/
    types.py

  classifier/
    types.py

  prior/
    types.py

  taxonomy/
    types.py

  pipeline/
    models.py
```

### `src/wild_catalog/core/types.py`

Use this file for small shared primitives that multiple services need.

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundingBox:
    xmin: int
    ymin: int
    xmax: int
    ymax: int

    @property
    def width(self) -> int:
        return self.xmax - self.xmin

    @property
    def height(self) -> int:
        return self.ymax - self.ymin
```

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GpsCoordinates:
    latitude: float
    longitude: float
```

### `src/wild_catalog/detection/types.py`

Use this file for detector output types. These should be model-agnostic so
Grounding DINO, a future YOLO variant, OWL-ViT, or another detector can all
return the same internal shape.

```python
from dataclasses import dataclass
from enum import StrEnum

from wild_catalog.core.types import BoundingBox


class DetectionCategory(StrEnum):
    ANIMAL = "animal"
    PLANT = "plant"
    FUNGUS = "fungus"
    LICHEN = "lichen"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Detection:
    bounding_box: BoundingBox
    confidence: float
    label: str
    category: DetectionCategory
    source: str
```

Example:

```python
Detection(
    bounding_box=BoundingBox(xmin=120, ymin=340, xmax=450, ymax=680),
    confidence=0.84,
    label="bird",
    category=DetectionCategory.ANIMAL,
    source="grounding-dino",
)
```

### `src/wild_catalog/cropping/types.py`

Use this file for crop results. The crop service owns margin logic, so it should
return both the original detection box and the margin-adjusted crop box.

```python
from dataclasses import dataclass

from PIL import Image

from wild_catalog.core.types import BoundingBox
from wild_catalog.detection.types import Detection


@dataclass(frozen=True, slots=True)
class CropResult:
    index: int
    detection: Detection
    bounding_box: BoundingBox
    bounding_box_with_margin: BoundingBox
    image: Image.Image
```

### `src/wild_catalog/classifier/types.py`

Use this file for classifier plugin metadata and classifier outputs.

Classifier plugins should expose their class-index metadata because the range
prior service and taxonomy service must align with the classifier's class order.

```python
from dataclasses import dataclass
from typing import Literal, Mapping

import torch


@dataclass(frozen=True, slots=True)
class ClassIndex:
    id: str
    taxon_id_by_class_id: Mapping[int, int]
```

```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ClassifierMetadata:
    backend: str
    model_id: str
    class_count: int
    class_index_id: str
    output_type: Literal["logits", "probabilities"]
    taxonomy_source: str
```

```python
from dataclasses import dataclass

import torch

from wild_catalog.classifier.types import ClassIndex


@dataclass(frozen=True, slots=True)
class RawClassifierOutput:
    logits: torch.Tensor
    class_index: ClassIndex
```

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassPrediction:
    class_id: int
    confidence: float
```

### `src/wild_catalog/prior/types.py`

Use this file for geographic prior and presence outputs.

The prior mask must align exactly with the active classifier's class index.

```python
from dataclasses import dataclass

import torch


@dataclass(frozen=True, slots=True)
class PriorMask:
    values: torch.Tensor
    class_index_id: str
```

```python
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class PresenceResult:
    is_present_by_taxon_id: Mapping[int, bool]
```

Use `is_present`, not `is_endemic`.

`is_present` means the predicted taxon is known, expected, or otherwise
geographically plausible for the provided location according to the Species
Range Prior Service.

### `src/wild_catalog/taxonomy/types.py`

Use this file for taxon records and enriched prediction output.

The taxonomy service owns scientific lineage, common names, localization
fallbacks, and taxonomy drift handling.

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaxonRecord:
    taxon_id: int
    parent_taxon_id: int | None
    rank: str
    scientific_name: str
    accepted_taxon_id: int | None = None
```

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnrichedPrediction:
    confidence: float
    is_present: bool
    taxonomy: tuple[str, ...]
    taxonomy_common_names: tuple[str, ...]
```

### `src/wild_catalog/pipeline/models.py`

Use this file for orchestration-level request and result objects that are not
HTTP-specific.

FastAPI request and response models should remain in `src/wild_catalog/api/`.
Pipeline models should represent the result of internal processing before it is
serialized into JSON or multipart output.

```python
from dataclasses import dataclass

from PIL import Image

from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.taxonomy.types import EnrichedPrediction


@dataclass(frozen=True, slots=True)
class IdentifiedObject:
    bounding_box: BoundingBox
    bounding_box_with_margin: BoundingBox
    gps_coordinates: GpsCoordinates | None
    predictions: tuple[EnrichedPrediction, ...]
    cropped_image: Image.Image | None = None
```

```python
from dataclasses import dataclass

from wild_catalog.pipeline.models import IdentifiedObject


@dataclass(frozen=True, slots=True)
class IdentifyResult:
    objects: tuple[IdentifiedObject, ...]
```

## Ownership Rules

Use these ownership rules when deciding where new classes belong:

| Type of class | Folder |
|---|---|
| Shared primitives used by many services | `src/wild_catalog/core/` |
| Detector output and detector metadata | `src/wild_catalog/detection/` |
| Crop output and crop metadata | `src/wild_catalog/cropping/` |
| Classifier outputs, logits, class-index metadata | `src/wild_catalog/classifier/` |
| Geographic prior masks and presence results | `src/wild_catalog/prior/` |
| Taxon records and enriched predictions | `src/wild_catalog/taxonomy/` |
| Internal end-to-end pipeline results | `src/wild_catalog/pipeline/` |
| HTTP request and response models | `src/wild_catalog/api/` |

## Design Rules

1. Prefer `@dataclass(frozen=True, slots=True)` for internal domain types.
2. Use Pydantic models only at API boundaries.
3. Keep detector-specific raw outputs inside detector adapters.
4. Keep classifier-specific raw outputs inside classifier adapters.
5. Convert plugin-specific outputs into stable Wild Catalog domain types before
   passing them deeper into the pipeline.
6. Do not let API models leak into service internals.
7. Do not let model-specific classes leak into the API response.
8. Do not store large images, tensors, or byte arrays in long-lived objects.
9. Use tuples for immutable sequences returned from pipeline-level results.
10. Keep `is_present` owned by the range/prior layer, even though it is attached
    to enriched taxonomy predictions for the final response.

---

## 4. Implement configuration

Create:

```text
src/wild_catalog/core/config.py
```

Use one central settings object for runtime configuration.

Recommended settings:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    env: str

    max_upload_bytes: int
    max_image_pixels: int
    max_detections: int
    crop_margin_ratio: float

    detector_backend: str
    classifier_backend: str

    preload_models: bool
    startup_synthetic_inference_enabled: bool
    max_concurrent_identify_requests: int

    enable_platform_image_conversion: bool
    platform_image_converter: str
    platform_conversion_timeout_seconds: int

    grounding_dino_model_id: str
    grounding_dino_prompt: str
    grounding_dino_box_threshold: float
    grounding_dino_text_threshold: float

    classifier_batch_size: int
    classifier_top_k: int
    classifier_model_cache_path: Path | None

    range_map_store_path: Path | None
    prior_epsilon: float
    prior_gamma: float

    taxonomy_dwca_url: str
    taxonomy_dwca_path: Path | None
    taxonomy_store_path: Path
    taxonomy_default_language: str
```

Recommended environment variables:

```text
WILD_CATALOG_ENV=development

WILD_CATALOG_MAX_UPLOAD_BYTES=26214400
WILD_CATALOG_MAX_IMAGE_PIXELS=24000000
WILD_CATALOG_MAX_DETECTIONS=8
WILD_CATALOG_CROP_MARGIN_RATIO=0.12

WILD_CATALOG_DETECTOR_BACKEND=grounding-dino
WILD_CATALOG_CLASSIFIER_BACKEND=birder-inat21

WILD_CATALOG_PRELOAD_MODELS=true
WILD_CATALOG_STARTUP_SYNTHETIC_INFERENCE_ENABLED=true
WILD_CATALOG_MAX_CONCURRENT_IDENTIFY_REQUESTS=1

WILD_CATALOG_ENABLE_PLATFORM_IMAGE_CONVERSION=true
WILD_CATALOG_PLATFORM_IMAGE_CONVERTER=auto
WILD_CATALOG_PLATFORM_CONVERSION_TIMEOUT_SECONDS=10

WILD_CATALOG_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-tiny
WILD_CATALOG_GROUNDING_DINO_BOX_THRESHOLD=0.25
WILD_CATALOG_GROUNDING_DINO_TEXT_THRESHOLD=0.25

WILD_CATALOG_SPECIES_CLASSIFIER_BATCH_SIZE=8
WILD_CATALOG_SPECIES_CLASSIFIER_TOP_K=12
WILD_CATALOG_SPECIES_CLASSIFIER_MODEL_CACHE_PATH=

WILD_CATALOG_RANGE_MAP_STORE_PATH=
WILD_CATALOG_PRIOR_EPSILON=0.01
WILD_CATALOG_PRIOR_GAMMA=1.0

WILD_CATALOG_TAXONOMY_DWCA_URL=https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip
WILD_CATALOG_TAXONOMY_DWCA_PATH=
WILD_CATALOG_TAXONOMY_STORE_PATH=data/taxonomy
WILD_CATALOG_TAXONOMY_DEFAULT_LANGUAGE=en-US
```

Keep configuration boring and explicit. Avoid hidden defaults scattered across
service implementations.

---

## 5. Implement shared device selection

Create:

```text
src/wild_catalog/core/device.py
```

Both detector and classifier plugins should use the same device helper.

Device priority:

1. Apple Silicon MPS.
2. CUDA.
3. CPU.

Recommended implementation shape:

```python
from functools import lru_cache

import torch


@lru_cache(maxsize=1)
def get_torch_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")

    if torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")
```

Do not duplicate device-selection logic inside individual model plugins.

---

## 6. Implement API request and response models

Create:

```text
src/wild_catalog/api/request_models.py
src/wild_catalog/api/response_models.py
```

Use Pydantic for API boundary models.

### `src/wild_catalog/api/request_models.py`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ExifOverrideRequest(BaseModel):
    gps_coordinates: str | None = Field(
        default=None,
        pattern=r"^-?\d+\.\d+,\s*-?\d+\.\d+$",
    )
    captured_at: datetime | None = None


class IdentifyRequest(BaseModel):
    original_filename: str
    exif_override: ExifOverrideRequest | None = None
    return_detected_images: bool = False
    common_name_language: str = "en-US"
```

### `src/wild_catalog/api/response_models.py`

```python
from pydantic import BaseModel


class BoundingBoxResponse(BaseModel):
    xmin: int
    ymin: int
    xmax: int
    ymax: int
    width: int
    height: int


class PredictionResponse(BaseModel):
    confidence: float
    is_present: bool
    taxonomy: list[str]
    taxonomy_common_names: list[str]


class IdentifiedObjectResponse(BaseModel):
    bounding_box: BoundingBoxResponse
    bounding_box_with_margin: BoundingBoxResponse
    gps_coordinates: tuple[float, float] | None
    predictions: list[PredictionResponse]
```

The `/identify` JSON response is a list of `IdentifiedObjectResponse`.

---

## 7. Implement the FastAPI app

Create:

```text
src/wild_catalog/api/app.py
```

Implement:

```text
GET /health
GET /status
GET /openapi.json
POST /identify
```

### `GET /health`

`GET /health` should remain lightweight.

It should not load models, validate range maps, parse taxonomy data, or run the
image identification pipeline.

Response:

```json
{
  "status": "ok"
}
```

### `GET /status`

`GET /status` reports startup readiness and warmup progress. Clients can poll it
to determine whether `POST /identify` is available.

`GET /status` should report:

1. Overall readiness.
2. Whether model preloading is enabled.
3. Per-task state.
4. Per-task progress where available.
5. Elapsed startup time.
6. Estimated time remaining where available.
7. Failure details for failed startup tasks.

`GET /status` must remain available while startup warming is running.

### `POST /identify`

`POST /identify` should accept multipart form data:

1. An uploaded image file.
2. A JSON payload form field.

Recommended endpoint shape:

```python
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response

from wild_catalog.api.dependencies import get_identify_pipeline
from wild_catalog.api.multipart import build_multipart_response
from wild_catalog.api.request_models import IdentifyRequest
from wild_catalog.pipeline.identify import IdentifyPipeline


app = FastAPI(title="Wild Catalog")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/identify")
async def identify(
    request: Request,
    image: Annotated[UploadFile, File()],
    payload: Annotated[str, Form()],
    pipeline: Annotated[IdentifyPipeline, Depends(get_identify_pipeline)],
) -> Response:
    identify_request = IdentifyRequest.model_validate_json(payload)

    result = await run_in_threadpool(
        pipeline.identify,
        image.file,
        identify_request,
    )

    if identify_request.return_detected_images:
        return build_multipart_response(result, include_images=True)

    accept_header = request.headers.get("accept")
    if accept_header and "multipart/mixed" in accept_header:
        return build_multipart_response(result, include_images=False)

    return JSONResponse(content=result_to_json(result))
```

Keep the actual conversion from pipeline result to API JSON in a small serializer
function.

---

## 8. Implement dependency wiring

Create:

```text
src/wild_catalog/api/dependencies.py
```

The API should build services through dependency providers and registries.
This module is the application composition root: it builds settings, detector
plugins, classifier plugins, shared services, and the `IdentifyPipeline`.
Use `@lru_cache(maxsize=1)` for settings. The FastAPI lifespan builds one identify pipeline, stores it in `app.state`, and `/identify` uses that same warmed pipeline. Do not warm one pipeline and serve requests with another.

The pipeline must receive dependencies through its constructor and must not
construct concrete detector or classifier plugins internally.

```python
from functools import lru_cache

from wild_catalog.classifier.registry import build_classifier
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.deduplication.service import DetectionDeduplicator
from wild_catalog.detection.registry import build_detector
from wild_catalog.pipeline.identify import IdentifyPipeline
from wild_catalog.prior.service import SpeciesRangePriorService
from wild_catalog.taxonomy.service import TaxonomyService


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def build_identify_pipeline(settings: Settings) -> IdentifyPipeline:
    return IdentifyPipeline(
        settings=settings,
        converter=ImageConversionService(settings),
        detector=build_detector(settings),
        deduplicator=DetectionDeduplicator(),
        cropper=ImageCropper(margin_ratio=settings.crop_margin_ratio),
        prior_service=SpeciesRangePriorService(settings),
        classifier=build_classifier(settings),
        conditioner=LogitConditioner(
            gamma=settings.prior_gamma,
            epsilon=settings.prior_epsilon,
            top_k=settings.classifier_top_k,
        ),
        taxonomy_service=TaxonomyService(settings),
    )


def get_identify_pipeline(request: Request) -> IdentifyPipeline:
    return request.app.state.identify_pipeline


def get_startup_status(request: Request) -> StartupStatusTracker:
    return request.app.state.startup_status


def clear_dependency_caches() -> None:
    get_settings.cache_clear()
```

Use FastAPI dependency overrides in tests to inject stub services. The lifespan stores the warmed pipeline and startup status in `app.state`; dependencies retrieve those application-scoped objects.

---

## 9. Implement image conversion

Create:

```text
src/wild_catalog/conversion/service.py
src/wild_catalog/conversion/format_sniffing.py
src/wild_catalog/conversion/exif.py
src/wild_catalog/conversion/standard.py
src/wild_catalog/conversion/raw.py
```

The image conversion service is responsible for:

1. Reading uploaded image data safely.
2. Enforcing upload size limits.
3. Sniffing image type.
4. Extracting EXIF metadata.
5. Converting supported formats to RGB.
6. Optionally invoking platform converters for HEIC/HEIF.
7. Returning a normalized Pillow RGB image and metadata.

Do not use `pillow-heif`.

### Supported direct formats

Directly supported by Python dependencies:

```text
JPEG / JPG
PNG
WebP
RAW formats supported by rawpy
```

### HEIC / HEIF

HEIC and HEIF are not decoded directly by Wild Catalog's Python image stack.

Instead, Wild Catalog may optionally use platform image conversion adapters.

Examples:

| Platform | Possible adapter |
|---|---|
| macOS | `sips` |
| Linux | ImageMagick with HEIC support, typically backed by libheif |
| Windows | ImageMagick with HEIC support, or Windows Imaging Component / PowerShell adapter |

All platform converters should be optional. If no compatible converter is
available, return a clear unsupported-format error.

### `src/wild_catalog/conversion/platform_conversion/protocols.py`

```python
from pathlib import Path
from typing import Protocol


class PlatformImageConverter(Protocol):
    def can_convert(self, detected_format: str) -> bool:
        ...

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        ...
```

### `src/wild_catalog/conversion/platform_conversion/noop.py`

```python
from pathlib import Path


class NoopPlatformImageConverter:
    def can_convert(self, detected_format: str) -> bool:
        return False

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        raise RuntimeError("No platform image converter is configured.")
```

### `src/wild_catalog/conversion/platform_conversion/macos_sips.py`

```python
import subprocess
from pathlib import Path


class MacOSSipsImageConverter:
    def __init__(
        self,
        sips_path: Path = Path("/usr/bin/sips"),
        timeout_seconds: int = 10,
    ) -> None:
        self._sips_path = sips_path
        self._timeout_seconds = timeout_seconds

    def can_convert(self, detected_format: str) -> bool:
        return detected_format.lower() in {"heic", "heif"}

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        subprocess.run(
            [
                str(self._sips_path),
                "-s",
                "format",
                "jpeg",
                str(source_path),
                "--out",
                str(output_path),
            ],
            check=True,
            timeout=self._timeout_seconds,
            capture_output=True,
            text=True,
        )
```

### `src/wild_catalog/conversion/platform_conversion/linux_imagemagick.py`

```python
import subprocess
from pathlib import Path


class LinuxImageMagickImageConverter:
    def __init__(
        self,
        magick_path: Path = Path("magick"),
        timeout_seconds: int = 10,
    ) -> None:
        self._magick_path = magick_path
        self._timeout_seconds = timeout_seconds

    def can_convert(self, detected_format: str) -> bool:
        return detected_format.lower() in {"heic", "heif"}

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        subprocess.run(
            [
                str(self._magick_path),
                str(source_path),
                str(output_path),
            ],
            check=True,
            timeout=self._timeout_seconds,
            capture_output=True,
            text=True,
        )
```

### `src/wild_catalog/conversion/platform_conversion/windows_imagemagick.py`

```python
import subprocess
from pathlib import Path


class WindowsImageMagickImageConverter:
    def __init__(
        self,
        magick_path: Path = Path("magick.exe"),
        timeout_seconds: int = 10,
    ) -> None:
        self._magick_path = magick_path
        self._timeout_seconds = timeout_seconds

    def can_convert(self, detected_format: str) -> bool:
        return detected_format.lower() in {"heic", "heif"}

    def convert_to_jpeg(self, source_path: Path, output_path: Path) -> None:
        subprocess.run(
            [
                str(self._magick_path),
                str(source_path),
                str(output_path),
            ],
            check=True,
            timeout=self._timeout_seconds,
            capture_output=True,
            text=True,
        )
```

### Safety rules for platform conversion

1. Use `subprocess.run([...], shell=False)`.
2. Never interpolate user input into a shell command.
3. Use a private temporary directory.
4. Enforce upload size before conversion.
5. Enforce max image pixels after conversion.
6. Use a timeout.
7. Capture stderr for logs, not raw API responses.
8. Clean up temporary files automatically.
9. Treat conversion failure as a controlled unsupported-format or
   unprocessable-entity error.

---

## 10. Implement pluggable detection

Create:

```text
src/wild_catalog/detection/protocols.py
src/wild_catalog/detection/registry.py
src/wild_catalog/detection/types.py
src/wild_catalog/detection/policy.py
src/wild_catalog/detection/stub.py
src/wild_catalog/detection/grounding_dino.py
src/wild_catalog/detection/grounding_dino_prompt.py
src/wild_catalog/detection/grounding_dino_postprocess.py
```

The detector should only answer:

```text
Where are candidate living things in this image?
```

It should not provide final species identity.

### `src/wild_catalog/detection/protocols.py`

```python
from typing import Protocol

from PIL import Image

from wild_catalog.detection.types import Detection


class ObjectDetector(Protocol):
    def locate_objects(self, image: Image.Image) -> list[Detection]:
        ...
```

### `src/wild_catalog/detection/grounding_dino_prompt.py`

```python
DEFAULT_GROUNDING_DINO_PROMPT = (
    "bird . mammal . animal . reptile . amphibian . fish . "
    "insect . butterfly . moth . beetle . dragonfly . spider . snail . "
    "flower . plant . tree . leaf . grass . moss . lichen . "
    "mushroom . fungus ."
)
```

### `src/wild_catalog/detection/policy.py`

```python
from wild_catalog.detection.types import DetectionCategory


DETECTION_CATEGORY_BY_LABEL = {
    "bird": DetectionCategory.ANIMAL,
    "mammal": DetectionCategory.ANIMAL,
    "animal": DetectionCategory.ANIMAL,
    "reptile": DetectionCategory.ANIMAL,
    "amphibian": DetectionCategory.ANIMAL,
    "fish": DetectionCategory.ANIMAL,
    "insect": DetectionCategory.ANIMAL,
    "butterfly": DetectionCategory.ANIMAL,
    "moth": DetectionCategory.ANIMAL,
    "beetle": DetectionCategory.ANIMAL,
    "dragonfly": DetectionCategory.ANIMAL,
    "spider": DetectionCategory.ANIMAL,
    "snail": DetectionCategory.ANIMAL,

    "flower": DetectionCategory.PLANT,
    "plant": DetectionCategory.PLANT,
    "tree": DetectionCategory.PLANT,
    "leaf": DetectionCategory.PLANT,
    "grass": DetectionCategory.PLANT,
    "moss": DetectionCategory.PLANT,

    "lichen": DetectionCategory.LICHEN,

    "mushroom": DetectionCategory.FUNGUS,
    "fungus": DetectionCategory.FUNGUS,
}


SPECIFICITY_RANK = {
    "animal": 1,
    "plant": 1,
    "fungus": 1,

    "mammal": 2,
    "reptile": 2,
    "amphibian": 2,
    "fish": 2,
    "insect": 2,
    "flower": 2,
    "tree": 2,
    "leaf": 2,
    "grass": 2,
    "moss": 2,
    "lichen": 2,
    "mushroom": 2,

    "bird": 3,
    "butterfly": 3,
    "moth": 3,
    "beetle": 3,
    "dragonfly": 3,
    "spider": 3,
    "snail": 3,
}


def normalize_detection_label(label: str) -> DetectionCategory | None:
    normalized = label.strip().lower()
    return DETECTION_CATEGORY_BY_LABEL.get(normalized)
```

### `src/wild_catalog/detection/registry.py`

```python
from wild_catalog.core.config import Settings
from wild_catalog.detection.protocols import ObjectDetector
from wild_catalog.detection.stub import StubObjectDetector
from wild_catalog.detection.grounding_dino import GroundingDinoObjectDetector


def build_detector(settings: Settings) -> ObjectDetector:
    if settings.detector_backend == "stub":
        return StubObjectDetector()

    if settings.detector_backend == "grounding-dino":
        return GroundingDinoObjectDetector(settings)

    raise ValueError(f"Unknown detector backend: {settings.detector_backend}")
```

The pipeline should depend on `ObjectDetector`, not on `GroundingDinoObjectDetector`
directly.

---

## 11. Implement deduplication

Create:

```text
src/wild_catalog/deduplication/iou.py
src/wild_catalog/deduplication/service.py
```

Deduplication removes overlapping detections that likely describe the same
organism.

Because Grounding DINO can return both broad and specific labels for the same
object, dedupe by detection category rather than exact text label.

Example overlapping labels:

```text
bird + animal
flower + plant
mushroom + fungus
```

### `src/wild_catalog/deduplication/iou.py`

```python
from wild_catalog.core.types import BoundingBox


def calculate_iou(a: BoundingBox, b: BoundingBox) -> float:
    x_left = max(a.xmin, b.xmin)
    y_top = max(a.ymin, b.ymin)
    x_right = min(a.xmax, b.xmax)
    y_bottom = min(a.ymax, b.ymax)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    a_area = a.width * a.height
    b_area = b.width * b.height
    union_area = a_area + b_area - intersection_area

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area
```

### `src/wild_catalog/deduplication/service.py`

```python
from wild_catalog.deduplication.iou import calculate_iou
from wild_catalog.detection.types import Detection


class DetectionDeduplicator:
    def __init__(self, iou_threshold: float = 0.45) -> None:
        self._iou_threshold = iou_threshold

    def filter_overlapping_detections(
        self,
        detections: list[Detection],
    ) -> list[Detection]:
        kept: list[Detection] = []

        for detection in sorted(
            detections,
            key=lambda item: item.confidence,
            reverse=True,
        ):
            duplicate = any(
                detection.category == kept_detection.category
                and calculate_iou(
                    detection.bounding_box,
                    kept_detection.bounding_box,
                )
                > self._iou_threshold
                for kept_detection in kept
            )

            if not duplicate:
                kept.append(detection)

        return kept
```

A later enhancement can prefer more-specific labels when confidence scores are
close. Start with highest confidence because it is easier to test and reason
about.

---

## 12. Implement cropping

Create:

```text
src/wild_catalog/cropping/service.py
src/wild_catalog/cropping/types.py
```

The cropper receives the normalized RGB image and deduplicated detections. It
applies margin padding, clamps bounds to image dimensions, and returns crops.

### `src/wild_catalog/cropping/service.py`

```python
from PIL import Image

from wild_catalog.core.types import BoundingBox
from wild_catalog.cropping.types import CropResult
from wild_catalog.detection.types import Detection


class ImageCropper:
    def __init__(self, margin_ratio: float) -> None:
        self._margin_ratio = margin_ratio

    def extract_target_regions(
        self,
        image: Image.Image,
        detections: list[Detection],
    ) -> list[CropResult]:
        results: list[CropResult] = []
        image_width, image_height = image.size

        for index, detection in enumerate(detections):
            box = detection.bounding_box
            margin_x = int(box.width * self._margin_ratio)
            margin_y = int(box.height * self._margin_ratio)

            crop_box = BoundingBox(
                xmin=max(0, box.xmin - margin_x),
                ymin=max(0, box.ymin - margin_y),
                xmax=min(image_width, box.xmax + margin_x),
                ymax=min(image_height, box.ymax + margin_y),
            )

            crop_image = image.crop(
                (
                    crop_box.xmin,
                    crop_box.ymin,
                    crop_box.xmax,
                    crop_box.ymax,
                )
            )

            results.append(
                CropResult(
                    index=index,
                    detection=detection,
                    bounding_box=box,
                    bounding_box_with_margin=crop_box,
                    image=crop_image,
                )
            )

        return results
```

Memory rule: only create crops after deduplication and after applying
`max_detections`.

---

## 13. Implement pluggable classification

Create:

```text
src/wild_catalog/classifier/protocols.py
src/wild_catalog/classifier/registry.py
src/wild_catalog/classifier/types.py
src/wild_catalog/classifier/stub.py
src/wild_catalog/classifier/birder.py
src/wild_catalog/classifier/transforms.py
```

The classifier should answer:

```text
Given one or more cropped organism images, what are the raw model scores?
```

Prefer raw logits over probabilities so the logit conditioning layer can apply
geographic priors before softmax.

### `src/wild_catalog/classifier/protocols.py`

```python
from typing import Protocol, Sequence

from PIL import Image

from wild_catalog.classifier.types import ClassifierMetadata, RawClassifierOutput


class SpeciesClassifier(Protocol):
    @property
    def metadata(self) -> ClassifierMetadata:
        ...

    def predict_species(
        self,
        cropped_images: Sequence[Image.Image],
    ) -> RawClassifierOutput:
        ...
```

### `src/wild_catalog/classifier/registry.py`

```python
from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.classifier.stub import StubSpeciesClassifier
from wild_catalog.core.config import Settings


def build_classifier(settings: Settings) -> SpeciesClassifier:
    if settings.classifier_backend == "stub":
        return StubSpeciesClassifier()

    if settings.classifier_backend == "birder-inat21":
        from wild_catalog.classifier.birder import BirderSpeciesClassifier

        return BirderSpeciesClassifier(settings)

    raise ValueError(f"Unknown classifier backend: {settings.classifier_backend}")
```

The pipeline should depend on `SpeciesClassifier`, not on `BirderSpeciesClassifier`
directly.

### Step 13A real Birder integration tests

Real Birder iNat21 integration tests live under:

```text
tests/integration/classifier/
```

They use realistic JPEG fixtures from:

```text
sample-images/
```

Use the existing project commands:

```bash
make test-fast
make test
make pr
```

The tests verify the `hieradet_d_small_dino-v2-inat21` adapter contract: model loading, RGB input handling, batching, raw logits, one row per input image, class-index metadata, and registry construction. The `20260402-IMG_7906.jpg` fixture is also checked for a cormorant label in the model's top predictions.

---

## 14. Implement species range prior service

Create:

```text
src/wild_catalog/prior/protocols.py
src/wild_catalog/prior/service.py
src/wild_catalog/prior/store.py
src/wild_catalog/prior/h3_index.py
src/wild_catalog/prior/types.py
src/wild_catalog/prior/stub.py
```

The prior service uses GPS coordinates and locally stored SQLite range-map data to:

1. Build a prior mask aligned with the active classifier class index.
2. Determine `is_present` for predicted taxa.

The prior service owns `is_present`.

The taxonomy service may attach `is_present` to enriched predictions, but it
should receive that value from the prior service.

### `src/wild_catalog/prior/protocols.py`

```python
from typing import Protocol

from wild_catalog.classifier.types import ClassIndex
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.types import PresenceResult, PriorMask


class SpeciesRangePrior(Protocol):
    def generate_prior_mask(
        self,
        gps_coordinates: GpsCoordinates | None,
        class_index: ClassIndex,
    ) -> PriorMask:
        ...

    def get_presence_for_taxa(
        self,
        gps_coordinates: GpsCoordinates | None,
        taxon_ids: set[int],
    ) -> PresenceResult:
        ...
```

Behavior:

1. If GPS is missing, return an all-ones prior mask.
2. If GPS is missing, treat `is_present` as `True`, because there is no location
   evidence against the taxon.
3. If GPS is present, query the local SQLite RTree for candidate range
   geometries at that point.
4. Use exact point-in-geometry checks to determine taxa known or plausible at
   that point.
5. Assign `1.0` to present taxa.
6. Assign epsilon to not-present taxa.
7. Return a mask with length equal to the classifier class count.

The request-time prior service must not download range maps, parse raw range-map
archives, or write the compiled SQLite range store.

### SQLite range store

The initial request-time schema is:

```sql
CREATE TABLE range_geometries (
    id INTEGER PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    min_lon REAL NOT NULL,
    min_lat REAL NOT NULL,
    max_lon REAL NOT NULL,
    max_lat REAL NOT NULL,
    geometry_wkb BLOB NOT NULL
);

CREATE VIRTUAL TABLE range_geometries_rtree USING rtree(
    id,
    min_lon,
    max_lon,
    min_lat,
    max_lat
);

CREATE INDEX idx_range_geometries_taxon_id
ON range_geometries (taxon_id);

CREATE TABLE range_store_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

The metadata table must include `source`, `source_version`, `geometry_format`,
and `built_at`.

## 14A. Build iNat21 range-map SQLite store

Create an offline or startup-managed process that downloads the iNat21 open
range maps in parallel, parses them, stores range geometry as WKB rows with an
SQLite RTree, and writes the local SQLite range store used by the Species Range
Prior Service.

This stage is not part of request-time `/identify` behavior.

Deliverables:

1. Config for the iNat21 range-map source URL or local archive path.
2. Parallel downloader or local-file loader.
3. GeoPackage parser for the range-map source format.
4. Geometry normalization and bounds extraction.
5. SQLite writer for `range_geometries` and `range_geometries_rtree`.
6. SQLite metadata writer for `range_store_metadata`.
7. Validation command or setup function.
8. Integration tests using a tiny fixture dataset.

Acceptance criteria:

1. The builder creates a valid SQLite database.
2. The database contains `range_geometries` and `range_geometries_rtree`.
3. The database contains `range_store_metadata`.
4. The metadata includes `geometry_format=wkb`.
5. The request-time app does not download range maps.
6. The request-time app does not parse raw range-map archives.
7. `/identify` only reads from the compiled SQLite store.
8. This is one of several pre-operational tasks to execute. These tasks can be
   run as a group through `make preop` and individually through specific `make`
   commands.

Startup integration can call the same pre-operational runner in a later
application startup step. Do not call pre-operational tasks from request-time
`/identify`, `IdentifyPipeline.identify`, or the request-time prior service.

Other pre-operational tasks include:
 * Downloading the detector model
 * Downloading the species classifier model

Implementation files:

```text
src/wild_catalog/preop/
src/wild_catalog/prior/build/
```

`src/wild_catalog/prior/build/geopackage.py` uses Pyogrio Arrow reads and
Shapely WKB conversion to avoid adding GeoPandas. `src/wild_catalog/prior/build/sqlite_staging.py`
contains optional SQLite `ATTACH` helpers for GeoPackage layer staging. H3 is not
used to precompute the primary store; it is only an optional request-time cache
key.

The pre-operational builder logs progress at regular intervals while processing
GeoPackage geometries so large range-map builds do not run silently. Include the
target SQLite database path, percent complete, processed range count, submitted
row count, and estimated time remaining in progress logs.

Range-cell rows must be streamed into SQLite in batches. Do not accumulate the
full H3 coverage in a Python set for the complete iNaturalist range-map corpus;
use the SQLite primary key plus `INSERT OR IGNORE` for deduplication.

Tests for the builder live under collected pytest paths such as:

```text
tests/unit/prior/test_build_metadata.py
tests/unit/prior/test_build_sqlite_writer.py
tests/unit/prior/test_build_validate.py
tests/unit/preop/test_runner.py
tests/integration/prior/test_range_store_builder.py
```

Avoid test directories named `build`, because pytest ignores those by default.

---

## 15. Implement logit conditioning

Create:

```text
src/wild_catalog/conditioning/service.py
```

The conditioning layer applies the geographic prior to classifier logits before
softmax.

Formula:

```text
z_conditioned = z_raw + gamma * log(G + epsilon)
```

Then softmax produces final probabilities.

### `src/wild_catalog/conditioning/service.py`

```python
import torch

from wild_catalog.classifier.types import ClassPrediction, RawClassifierOutput
from wild_catalog.prior.types import PriorMask


class LogitConditioner:
    def __init__(
        self,
        gamma: float,
        epsilon: float,
        top_k: int,
    ) -> None:
        self._gamma = gamma
        self._epsilon = epsilon
        self._top_k = top_k

    def apply_geographic_prior(
        self,
        classifier_output: RawClassifierOutput,
        prior_mask: PriorMask,
    ) -> list[list[ClassPrediction]]:
        logits = classifier_output.logits

        if classifier_output.class_index.id != prior_mask.class_index_id:
            raise ValueError(
                "Prior mask class index does not match classifier output."
            )

        prior_values = prior_mask.values.to(
            device=logits.device,
            dtype=logits.dtype,
        )

        safe_prior = torch.clamp(prior_values, min=self._epsilon)
        conditioned_logits = logits + self._gamma * torch.log(safe_prior)
        probabilities = torch.softmax(conditioned_logits, dim=-1)

        top_probabilities, top_indices = torch.topk(
            probabilities,
            k=self._top_k,
            dim=-1,
        )

        results: list[list[ClassPrediction]] = []

        for crop_probabilities, crop_indices in zip(
            top_probabilities,
            top_indices,
            strict=True,
        ):
            crop_predictions = [
                ClassPrediction(
                    class_id=int(class_id),
                    confidence=float(confidence),
                )
                for confidence, class_id in zip(
                    crop_probabilities.detach().cpu(),
                    crop_indices.detach().cpu(),
                    strict=True,
                )
            ]
            results.append(crop_predictions)

        return results
```

Keep this layer free of image, HTTP, taxonomy, and detector concerns.

---

## 16. Implement taxonomy service

Create:

```text
src/wild_catalog/taxonomy/protocols.py
src/wild_catalog/taxonomy/service.py
src/wild_catalog/taxonomy/store.py
src/wild_catalog/taxonomy/dwca.py
src/wild_catalog/taxonomy/types.py
src/wild_catalog/taxonomy/stub.py
```

The taxonomy service enriches classifier predictions with:

1. Scientific taxonomy lineage.
2. Localized common names.
3. Taxonomy drift handling.
4. Fallback common-name behavior.
5. `is_present` values supplied by the species range prior service.

It uses the iNaturalist Taxonomy DarwinCore Archive, `taxonomy.dwca.zip`, as the
local source of truth.

Do not call live iNaturalist APIs during `/identify`.
Do not download or parse `taxonomy.dwca.zip` during `/identify`; request-time
taxonomy enrichment should use local lookup data prepared before requests.
`make preop` includes a taxonomy download task that reuses an existing non-empty
local archive and downloads the configured iNaturalist Taxonomy DarwinCore
Archive when it is missing.

### `src/wild_catalog/taxonomy/protocols.py`

```python
from typing import Mapping, Protocol, Sequence

from wild_catalog.classifier.types import ClassIndex, ClassPrediction
from wild_catalog.taxonomy.types import EnrichedPrediction


class TaxonomyServiceProtocol(Protocol):
    def resolve_class_index(self, class_index: ClassIndex) -> ClassIndex:
        ...

    def enrich_predictions(
        self,
        predictions: Sequence[ClassPrediction],
        class_index: ClassIndex,
        common_name_language: str,
        presence_by_taxon_id: Mapping[int, bool],
    ) -> list[EnrichedPrediction]:
        ...
```

### Common name fallback order

1. Requested locale exact match.
2. Requested language without region.
3. Project default locale.
4. Any English common name.
5. Scientific name.

When multiple common names match the same fallback tier, use metadata from the
local DarwinCore Archive row where available to choose among them. Do not
hard-code species-specific common-name preferences.

### Taxonomy drift handling

Taxonomy drift belongs to the taxonomy service. Classifier plugins may expose
their model-training scientific names and label lineage metadata, but they must
not hard-code taxonomy drift maps.

The taxonomy service should resolve drift from the local DWCA store:

1. Try the classifier-provided model scientific name as an exact taxonomy-store
   lookup.
2. Resolve accepted taxon IDs where the DWCA record supplies one.
3. When the model scientific name is stale, use model lineage context plus the
   local taxonomy store to find a current taxon where the match is reliable.
4. Fall back to the classifier-provided taxon ID when no reliable local taxonomy
   match exists.

Callers that apply geographic priors should use
`TaxonomyServiceProtocol.resolve_class_index()` before prior-mask generation so
the prior service sees the same current taxon IDs that enrichment returns.

### Taxonomy service responsibilities

The taxonomy service is responsible for:

1. Mapping classifier class IDs to taxon IDs.
2. Resolving accepted taxon IDs where appropriate.
3. Walking parent links to build scientific lineage.
4. Resolving common names for each lineage rank.
5. Returning arrays where `taxonomy` and `taxonomy_common_names` have matching
   indexes.
6. Attaching `is_present` values received from the prior service.
7. Resolving classifier class-index taxon IDs before geographic prior generation.
8. Handling unknown class IDs with controlled errors.

### Pre-operational taxonomy download

The pre-operational task `download-taxonomy-dwca` downloads
`taxonomy.dwca.zip` to the configured local taxonomy archive path. The real DWCA
integration test uses the same downloader and downloads the archive under the
full integration-test gate if it is not already present.

---

## 17. Implement the orchestration pipeline

Create:

```text
src/wild_catalog/pipeline/identify.py
src/wild_catalog/pipeline/models.py
```

The pipeline coordinates the services.

The pipeline should not know about FastAPI, multipart responses, HTTP headers, or
specific model implementations.

### `src/wild_catalog/pipeline/identify.py`

```python
from typing import BinaryIO

from wild_catalog.api.request_models import IdentifyRequest
from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.deduplication.service import DetectionDeduplicator
from wild_catalog.detection.protocols import ObjectDetector
from wild_catalog.pipeline.models import IdentifiedObject, IdentifyResult
from wild_catalog.prior.protocols import SpeciesRangePrior
from wild_catalog.taxonomy.protocols import TaxonomyServiceProtocol


class IdentifyPipeline:
    def __init__(
        self,
        settings: Settings,
        converter: ImageConversionService,
        detector: ObjectDetector,
        deduplicator: DetectionDeduplicator,
        cropper: ImageCropper,
        prior_service: SpeciesRangePrior,
        classifier: SpeciesClassifier,
        conditioner: LogitConditioner,
        taxonomy_service: TaxonomyServiceProtocol,
    ) -> None:
        self._settings = settings
        self._converter = converter
        self._detector = detector
        self._deduplicator = deduplicator
        self._cropper = cropper
        self._prior_service = prior_service
        self._classifier = classifier
        self._conditioner = conditioner
        self._taxonomy_service = taxonomy_service

    def identify(
        self,
        image_file: BinaryIO,
        request: IdentifyRequest,
    ) -> IdentifyResult:
        converted = self._converter.process_and_extract_metadata(
            image_file=image_file,
            original_filename=request.original_filename,
            exif_override=request.exif_override,
        )

        detections = self._detector.locate_objects(converted.image)

        deduplicated_detections = self._deduplicator.filter_overlapping_detections(
            detections
        )

        limited_detections = deduplicated_detections[: self._settings.max_detections]

        crop_results = self._cropper.extract_target_regions(
            image=converted.image,
            detections=limited_detections,
        )

        cropped_images = [crop.image for crop in crop_results]

        if not cropped_images:
            return IdentifyResult(objects=())

        classifier_output = self._classifier.predict_species(cropped_images)

        prior_mask = self._prior_service.generate_prior_mask(
            gps_coordinates=converted.gps_coordinates,
            class_index=classifier_output.class_index,
        )

        predictions_by_crop = self._conditioner.apply_geographic_prior(
            classifier_output=classifier_output,
            prior_mask=prior_mask,
        )

        all_taxon_ids = {
            classifier_output.class_index.taxon_id_by_class_id[prediction.class_id]
            for crop_predictions in predictions_by_crop
            for prediction in crop_predictions
        }

        presence = self._prior_service.get_presence_for_taxa(
            gps_coordinates=converted.gps_coordinates,
            taxon_ids=all_taxon_ids,
        )

        identified_objects: list[IdentifiedObject] = []

        for crop, crop_predictions in zip(
            crop_results,
            predictions_by_crop,
            strict=True,
        ):
            enriched_predictions = self._taxonomy_service.enrich_predictions(
                predictions=crop_predictions,
                class_index=classifier_output.class_index,
                common_name_language=request.common_name_language,
                presence_by_taxon_id=presence.is_present_by_taxon_id,
            )

            identified_objects.append(
                IdentifiedObject(
                    bounding_box=crop.bounding_box,
                    bounding_box_with_margin=crop.bounding_box_with_margin,
                    gps_coordinates=converted.gps_coordinates,
                    predictions=tuple(enriched_predictions),
                    cropped_image=(
                        crop.image if request.return_detected_images else None
                    ),
                )
            )

        return IdentifyResult(objects=tuple(identified_objects))
```

If you want to keep API models fully out of the pipeline, replace
`IdentifyRequest` with a pipeline-specific request dataclass later. For an early
implementation, using the API request model here is acceptable, but the cleaner
long-term design is to keep them separate.

---

## 18. Implement content negotiation and multipart responses

Create:

```text
src/wild_catalog/api/content_negotiation.py
src/wild_catalog/api/multipart.py
```

Response behavior:

1. If `return_detected_images=true` and `Accept` allows `multipart/mixed`,
   `multipart/*`, or `*/*`, return `multipart/mixed`.
2. If `return_detected_images=true` and `Accept` is missing, return
   `multipart/mixed`.
3. If `return_detected_images=true` and `Accept` does not allow
   `multipart/mixed`, return `406 Not Acceptable`.
4. If `return_detected_images=false` and `Accept` includes `application/json`,
   return normal JSON, even when `multipart/mixed` is also accepted.
5. If `return_detected_images=false` and `Accept` includes `multipart/mixed`
   but not `application/json`, return multipart with only the JSON part.
6. Otherwise return normal JSON.

The first multipart part must always be the JSON payload.

Subsequent parts contain crop JPEGs only when `return_detected_images=true`.

Do not base64 encode crop images.

Multipart part headers:

```text
Part 1:
  Content-Type: application/json; charset=utf-8
  Content-Disposition: inline; name="metadata"

Part 2+:
  Content-Type: image/jpeg
  Content-Disposition: attachment; name="crop-{index}"; filename="crop-{index}.jpg"
```

---

## 19. Implement error handling

Create:

```text
src/wild_catalog/api/errors.py
```

Use clear error types.

Recommended HTTP statuses:

| Status | Use case |
|---|---|
| `400 Bad Request` | Malformed JSON payload, invalid GPS override |
| `406 Not Acceptable` | `return_detected_images=true` but `Accept` does not allow `multipart/mixed` |
| `413 Payload Too Large` | Upload exceeds configured size |
| `415 Unsupported Media Type` | Unsupported image format |
| `422 Unprocessable Entity` | Corrupt image, failed platform conversion |
| `503 Service Unavailable` | Required model or local data unavailable, startup still warming, or startup failed |
| `500 Internal Server Error` | Unexpected failure |

Do not expose stack traces or raw command stderr in API responses.

Do log enough detail for debugging.

---

## 20. Implement startup pre-warming and status API

Use FastAPI lifespan support in:

```text
src/wild_catalog/api/app.py
```

Create startup/status support files:

```text
src/wild_catalog/startup/__init__.py
src/wild_catalog/startup/status.py
src/wild_catalog/startup/tasks.py
src/wild_catalog/startup/warmup.py

src/wild_catalog/api/status_models.py
src/wild_catalog/api/status_serializers.py
src/wild_catalog/api/readiness.py
```

### Startup behavior

Default behavior is eager preloading:

```text
WILD_CATALOG_PRELOAD_MODELS=true
```

Startup should:

1. Build settings.
2. Build one identify pipeline.
3. Store the pipeline in `app.state`.
4. Start warmup tasks.
5. Track per-task status and progress.
6. Mark the backend ready only after required warmup tasks complete.
7. Log startup timing.

When `WILD_CATALOG_PRELOAD_MODELS=true`, startup should warm:

1. Detector model.
2. Classifier model.
3. Taxonomy store.
4. Range prior store.
5. Optional tiny synthetic inference.

Recommended setting:

```text
WILD_CATALOG_STARTUP_SYNTHETIC_INFERENCE_ENABLED=true
```

`WILD_CATALOG_PRELOAD_MODELS=false` is a development opt-out. It should allow
the backend to become ready without eagerly loading heavy models. Do not make
lazy loading the default.

### Background warmup requirement

Startup warmup should run in the background rather than blocking the FastAPI app
from serving all requests.

This allows:

```text
GET /status
```

to be available immediately while startup warming is still running.

During this period:

```text
POST /identify
```

must not run the expensive identification pipeline.

Instead, it should return:

```text
503 Service Unavailable
```

### `POST /identify` not-ready behavior

If `/identify` is called before warmup completes, return:

```text
503 Service Unavailable
```

with an error body like:

```json
{
  "error": {
    "code": "service_not_ready",
    "message": "Wild Catalog is still warming required models and local data. Call GET /status for startup progress and estimated readiness.",
    "request_id": "..."
  }
}
```

If startup failed, return:

```json
{
  "error": {
    "code": "startup_failed",
    "message": "Wild Catalog startup failed while preparing required models or local data. Call GET /status for failure details.",
    "request_id": "..."
  }
}
```

When a reasonable estimate is available, include:

```http
Retry-After: 10
```

The `503` message must explicitly tell clients that `GET /status` provides more
information.

### `GET /status`

Add:

```text
GET /status
```

`GET /status` should be available while startup warming is still running.

It should return:

1. Overall startup state.
2. `ready`.
3. `preload_models`.
4. Startup `started_at`.
5. Startup `finished_at`.
6. Startup `elapsed_seconds`.
7. Overall `estimated_seconds_remaining`.
8. Per-task progress.

Recommended response shape:

```json
{
  "state": "starting",
  "ready": false,
  "preload_models": true,
  "started_at": "2026-06-07T21:42:35.729Z",
  "finished_at": null,
  "elapsed_seconds": 18.2,
  "estimated_seconds_remaining": 42.0,
  "tasks": [
    {
      "name": "detector-model",
      "state": "succeeded",
      "progress_current": null,
      "progress_total": null,
      "progress_percent": null,
      "message": "Detector model is ready.",
      "started_at": "2026-06-07T21:42:35.729Z",
      "finished_at": "2026-06-07T21:42:41.100Z",
      "elapsed_seconds": 5.37,
      "estimated_seconds_remaining": null,
      "error_code": null,
      "error_message": null
    },
    {
      "name": "classifier-model",
      "state": "running",
      "progress_current": null,
      "progress_total": null,
      "progress_percent": null,
      "message": "Loading classifier model.",
      "started_at": "2026-06-07T21:42:41.101Z",
      "finished_at": null,
      "elapsed_seconds": 12.8,
      "estimated_seconds_remaining": 42.0,
      "error_code": null,
      "error_message": null
    }
  ]
}
```

Task states:

```text
pending
running
succeeded
failed
skipped
```

Overall states:

```text
starting
ready
failed
```

### Startup status tracker

Implement a thread-safe startup status tracker in:

```text
src/wild_catalog/startup/status.py
```

It should support:

1. Registering tasks.
2. Marking tasks pending, running, succeeded, failed, or skipped.
3. Updating progress.
4. Capturing task messages.
5. Capturing task errors.
6. Capturing elapsed time.
7. Capturing estimated time remaining.
8. Creating immutable snapshots for API serialization.

Use a lock because `/status` may be read while warmup tasks are updating state.

### Startup warmup tasks

Implement startup warmup orchestration in:

```text
src/wild_catalog/startup/tasks.py
src/wild_catalog/startup/warmup.py
```

Recommended startup tasks:

```text
detector-model
classifier-model
taxonomy-store
range-prior-store
synthetic-inference
```

Run tasks sequentially first for simpler debugging and lower peak memory usage.

A later optimization can run independent tasks in parallel after measuring memory
and GPU contention.

### Pipeline warmup hooks

Add explicit warmup hooks to:

```text
src/wild_catalog/pipeline/identify.py
```

Recommended methods:

```python
def detector_warmup(self) -> None:
    ...

def classifier_warmup(self) -> None:
    ...

def taxonomy_warmup(self) -> None:
    ...

def prior_warmup(self) -> None:
    ...

def synthetic_warmup(self, image: Image.Image) -> None:
    ...
```

Model and store services may expose their own `warmup()` methods. The pipeline
warmup hooks should call those where available.

### Store/model warmup expectations

Detector warmup should load the detector model.

Classifier warmup should load the classifier model.

Taxonomy warmup should load or validate the taxonomy lookup store.

Range prior warmup should open and lightly validate the SQLite range prior store.

Synthetic inference should run a tiny image through detector/classifier warmup
paths to force lazy tensor/model initialization.

### Do not rebuild durable data on every startup

Startup should not automatically rebuild large durable pre-operational data
assets every time the app starts.

Startup should warm and validate existing assets:

```text
detector model cache
classifier model cache
taxonomy archive or compiled taxonomy store
range-map SQLite store
```

If required local data is missing, startup should mark the relevant task failed
and `/identify` should return `503`.

Use `make preop` and specific preop commands to prepare durable assets.

Do not call `make` from FastAPI startup.

Do not run shell commands from startup to rebuild all range maps.

### Readiness guard

Create:

```text
src/wild_catalog/api/readiness.py
```

The `/identify` endpoint should check readiness before running expensive work.

Recommended behavior:

1. If startup status is ready, continue.
2. If startup status is still starting, raise `ServiceNotReadyError`.
3. If startup status failed, raise `StartupFailedError`.

The readiness guard should include `Retry-After` when an estimated time remaining
exists.

Recommended order inside `/identify`:

1. Check readiness.
2. Parse request payload.
3. Run content negotiation.
4. Run pipeline.
5. Build response.

This means malformed requests may receive `503` during startup warming because
`/identify` is temporarily unavailable. This is acceptable and protects the
warming server from unnecessary request work.

### Dependency wiring

`src/wild_catalog/api/dependencies.py` should expose:

```python
def build_identify_pipeline(settings: Settings) -> IdentifyPipeline:
    ...

def get_identify_pipeline(request: Request) -> IdentifyPipeline:
    return request.app.state.identify_pipeline

def get_startup_status(request: Request) -> StartupStatusTracker:
    return request.app.state.startup_status
```

The warmed pipeline stored in `app.state` must be the same pipeline used by
`POST /identify`.

Avoid warming one pipeline and serving requests through a different pipeline.

### Lifespan implementation

Use FastAPI lifespan in:

```text
src/wild_catalog/api/app.py
```

The app should:

1. Build settings.
2. Build the identify pipeline.
3. Create startup status tracker.
4. Store settings, pipeline, and status tracker in `app.state`.
5. If preloading is enabled, submit warmup to a background executor.
6. If preloading is disabled, mark preload as skipped and mark the service ready.
7. Shut down the warmup executor on application shutdown.

### `GET /health`

`GET /health` remains lightweight.

It should not:

```text
load models
check range-map data
parse taxonomy data
run synthetic inference
report readiness
```

It should continue to return:

```json
{
  "status": "ok"
}
```

Use `GET /status` for readiness.

### Client behavior

Clients should use this flow:

1. Start backend.
2. Poll `GET /status`.
3. Wait for `ready=true`.
4. Call `POST /identify`.
5. If `POST /identify` returns `503`, call `GET /status` and retry later.

### Tests

Add unit tests for:

```text
tests/unit/startup/test_status.py
tests/unit/api/test_readiness.py
tests/unit/api/test_status_serializers.py
tests/unit/api/test_status_endpoint.py
tests/unit/api/test_identify_readiness.py
```

Update existing API tests that exercise `/identify` to override startup status as
ready. Otherwise, those tests may now receive `503` before testing their intended
behavior.

Test cases should include:

1. Status tracker reports running task progress.
2. Status tracker reports ready state.
3. Status tracker reports failed state.
4. `/status` returns startup state.
5. `/identify` returns `503 service_not_ready` when warmup is running.
6. `/identify` returns `503 startup_failed` when warmup failed.
7. `/identify` not-ready response mentions `GET /status`.
8. `Retry-After` is set when an estimate is available.
9. Existing `/identify` response behavior tests set startup status to ready.

### Documentation

Document:

```text
WILD_CATALOG_PRELOAD_MODELS defaults to true.
WILD_CATALOG_PRELOAD_MODELS=false is development opt-out behavior.
GET /health is lightweight.
GET /status reports readiness and warmup progress.
POST /identify returns 503 until startup warming completes.
POST /identify 503 responses tell clients to call GET /status.
Retry-After may be included when an estimate is available.
make serve may start the HTTP server quickly, but /identify is unavailable until ready.
```

Acceptance criteria:

1. FastAPI lifespan support is used.
2. `WILD_CATALOG_PRELOAD_MODELS` defaults to `true`.
3. `WILD_CATALOG_PRELOAD_MODELS=false` is supported for development opt-out.
4. Startup builds settings.
5. Startup builds one identify pipeline.
6. Startup stores the warmed pipeline in `app.state`.
7. `/identify` uses the same pipeline that startup warmed.
8. Startup warms detector model by default.
9. Startup warms classifier model by default.
10. Startup warms taxonomy store by default.
11. Startup opens or validates range prior store by default.
12. Startup optionally runs tiny synthetic inference.
13. Startup logs timing.
14. Startup status tracker exists and is thread-safe.
15. `GET /status` exists.
16. `GET /status` is available while startup warmup is running.
17. `GET /status` returns `ready=false` while warming.
18. `GET /status` returns `ready=true` when warmup completes.
19. `GET /status` returns per-task state.
20. `GET /status` returns per-task progress when available.
21. `GET /status` returns elapsed time.
22. `GET /status` returns estimated time remaining when available.
23. `GET /status` returns task failure details when startup fails.
24. `POST /identify` returns `503` while startup is still warming.
25. `POST /identify` 503 response uses error code `service_not_ready`.
26. `POST /identify` 503 response tells clients to call `GET /status`.
27. `POST /identify` includes `Retry-After` when a reasonable estimate exists.
28. `POST /identify` returns `503` with error code `startup_failed` if warmup failed.
29. `POST /identify` does not run expensive pipeline work before readiness check.
30. `GET /health` remains lightweight.
31. `GET /health` does not load models.
32. `GET /health` does not check local data.
33. Existing API tests override startup status to ready where needed.
34. Unit tests live under `tests/unit/`.
35. No tests are created directly under `tests/`.
36. No Makefile changes are made.
37. `make test-fast` passes.
38. `make lint` passes.
39. `make test` passes.
40. `make pr` passes.


---

## 21. Add bounded concurrency

Real model inference can consume significant memory.

Add a concurrency guard around the identify pipeline.

Create:

```text
src/wild_catalog/api/dependencies.py
```

or a small helper in:

```text
src/wild_catalog/core/concurrency.py
```

Recommended setting:

```text
WILD_CATALOG_MAX_CONCURRENT_IDENTIFY_REQUESTS=1
```

Start conservative. Increase only after measuring memory and latency.

---

## 22. Add timing instrumentation

Create:

```text
src/wild_catalog/core/timing.py
```

Track:

```text
conversion_ms
detection_ms
deduplication_ms
cropping_ms
prior_ms
classification_ms
conditioning_ms
taxonomy_ms
serialization_ms
total_ms
```

Do not include timing data in normal public responses.

Log timing data with a request ID.

Optionally expose a debug header in development:

```text
X-Wild-Catalog-Total-Time-Ms
```

---

## 23. Testing strategy

Use default tests with stubs.

Real model tests should be opt-in.

Recommended test folders:

```text
tests/unit/api/
tests/unit/conversion/
tests/unit/detection/
tests/unit/deduplication/
tests/unit/cropping/
tests/unit/classifier/
tests/unit/prior/
tests/unit/conditioning/
tests/unit/taxonomy/
tests/unit/pipeline/
tests/unit/architecture/
tests/integration/conversion/
tests/integration/detection/
tests/integration/classifier/
tests/integration/taxonomy/
tests/integration/pipeline/
```

### Unit tests

Add unit tests for:

1. GPS parsing.
2. EXIF override precedence.
3. Image format sniffing.
4. Unsupported HEIC/HEIF behavior when no converter exists.
5. Platform converter command construction using mocks.
6. RGB conversion.
7. Grounding DINO prompt contents.
8. Detection label normalization.
9. IoU calculation.
10. Deduplication behavior.
11. Crop margin and clamping.
12. Missing-GPS prior mask.
13. Class-index mismatch errors.
14. Logit conditioning math.
15. Top-k selection.
16. Taxonomy lineage resolution.
17. Common-name fallback.
18. `is_present` propagation.
19. JSON serialization.
20. Multipart response formatting.

### API tests

Test:

1. `GET /health`.
2. `GET /openapi.json`.
3. `POST /identify` with stub services and JSON response.
4. `POST /identify` with `Accept: multipart/mixed`.
5. `POST /identify` with `return_detected_images=true`.
6. Invalid JSON payload.
7. Oversized upload.
8. Unsupported image.
9. Missing required `original_filename`.

### Contract tests

Every detector plugin should pass tests proving that it:

1. Returns pixel `xyxy` boxes.
2. Keeps boxes inside image bounds.
3. Returns normalized categories.
4. Does not return people as target detections.
5. Can be built from settings.

Every classifier plugin should pass tests proving that it:

1. Returns one output row per crop.
2. Exposes class-index metadata.
3. Returns logits or explicitly declares otherwise.
4. Produces outputs that can feed the conditioning layer.
5. Can be built from settings.

### Integration tests

Integration tests should be opt-in for:

1. Real Grounding DINO loading.
2. Real Birder classifier loading.
3. Real iNaturalist taxonomy archive parsing.
4. Real range-map lookup.
5. End-to-end identification with fixture images.

Use small fixture data for default CI.

---

## 24. Performance and memory rules

### Hot path rules

1. Do not download models during `/identify`.
2. Do not parse `taxonomy.dwca.zip` during `/identify`.
3. Do not call live iNaturalist APIs during `/identify`.
4. Do not compile range maps during `/identify`.
5. Do not base64 encode images.
6. Do not create crops before deduplication.
7. Do not classify more detections than `max_detections`.
8. Do not instantiate models per request.
9. Do not duplicate large image byte arrays.
10. Do not keep tensors longer than necessary.

### Memory rules

1. Read uploads once.
2. Use temporary files for platform conversion.
3. Normalize to one RGB image.
4. Crop only deduplicated detections.
5. Batch classifier inputs.
6. Return crop images only when requested.
7. Use `torch.inference_mode()`.
8. Use immutable dataclasses for small domain objects.
9. Avoid long-lived references to Pillow images.
10. Keep taxonomy and range stores compact and read-only where practical.

---

## 25. Milestones

### Milestone 1: API shell with stubs

Deliverables:

1. FastAPI app.
2. `/health`.
3. `/identify`.
4. API request and response models.
5. Stub detector.
6. Stub classifier.
7. Stub prior service.
8. Stub taxonomy service.
9. JSON response tests.
10. Multipart response tests.

Acceptance criteria:

1. `make test-fast` passes.
2. Stub `/identify` completes under 500ms.
3. No real models are required.

---

### Milestone 2: Image conversion

Deliverables:

1. Format sniffing.
2. Pillow standard image path.
3. RAW path with `rawpy`.
4. EXIF extraction.
5. GPS extraction.
6. EXIF override handling.
7. Platform conversion protocol.
8. No-op converter.
9. macOS `sips` converter.
10. Linux ImageMagick converter.
11. Windows ImageMagick converter.

Acceptance criteria:

1. JPEG converts to RGB.
2. PNG converts to RGB.
3. WebP converts to RGB.
4. RAW fixtures convert when available.
5. HEIC/HEIF returns a controlled error if no converter is available.
6. Platform converters are tested with mocked subprocess calls.
7. `pillow-heif` is not required.

---

### Milestone 3: Pluggable detector framework and Grounding DINO plugin

Deliverables:

1. `ObjectDetector` protocol.
2. Detector registry.
3. Detection domain types.
4. Grounding DINO prompt config.
5. Grounding DINO adapter.
6. Label normalization.
7. Detector contract tests.

Acceptance criteria:

1. `stub` detector works without model dependencies.
2. `grounding-dino` detector can be selected by config.
3. Unknown detector backend fails with a clear error.
4. Pipeline does not import Grounding DINO directly.
5. Detector output uses stable Wild Catalog `Detection` objects.

---

### Milestone 4: Deduplication and cropping

Deliverables:

1. IoU calculation.
2. Category-aware deduplication.
3. Crop margin logic.
4. Crop clamping.
5. Crop result types.

Acceptance criteria:

1. Overlapping `bird` and `animal` boxes dedupe.
2. Overlapping `flower` and `plant` boxes dedupe.
3. Non-overlapping same-category boxes are kept.
4. Crops stay inside image bounds.
5. Crops are only generated after deduplication.

---

### Milestone 5: Pluggable classifier framework and Birder plugin

Deliverables:

1. `SpeciesClassifier` protocol.
2. Classifier registry.
3. Classifier metadata.
4. Class index metadata.
5. Stub classifier.
6. Birder iNat21 classifier plugin.
7. Classifier contract tests.

Acceptance criteria:

1. `stub` classifier works without model dependencies.
2. `birder-inat21` classifier can be selected by config.
3. Unknown classifier backend fails with a clear error.
4. Pipeline does not import Birder directly.
5. Classifier output includes class-index metadata.

---

### Milestone 6: Range prior and logit conditioning

Deliverables:

1. Species range prior protocol.
2. Prior mask type.
3. Presence result type.
4. H3 coordinate mapping.
5. Local range map store.
6. Logit conditioning layer.
7. Top-k conditioned predictions.

Acceptance criteria:

1. Missing GPS returns an all-ones prior mask.
2. Present taxa receive a high prior value.
3. Not-present taxa receive epsilon.
4. Prior mask class index must match classifier output class index.
5. Conditioning tests prove the formula works.
6. `is_present` is produced by the prior layer.

---

### Milestone 7: Taxonomy service

Deliverables:

1. Taxonomy service protocol.
2. Taxonomy types.
3. Stub taxonomy service.
4. DarwinCore Archive loader.
5. Compiled taxonomy lookup store.
6. Common-name fallback.
7. Taxonomy lineage resolution.
8. Taxonomy drift mapping support.

Acceptance criteria:

1. Class ID maps to taxon ID.
2. Taxon ID maps to scientific lineage.
3. Common names resolve for `en-US`.
4. Locale fallback works.
5. Missing common names fall back to scientific names.
6. `taxonomy` and `taxonomy_common_names` arrays have matching lengths.
7. `/identify` does not parse the full archive at request time.

---

### Milestone 8: Production readiness

Deliverables:

1. Startup pre-warming and `GET /status` readiness reporting.
2. Bounded concurrency.
3. Timing logs.
4. Request IDs.
5. Controlled error responses.
6. Performance tests.
7. Memory tests.

Acceptance criteria:

1. Warm stub request stays under 500ms.
2. Warm real-model benchmark is measured and documented.
3. Cold-start behavior is documented separately.
4. Repeated requests do not leak memory.
5. Full test suite passes.

---

## 26. Final implementation order

Build in this order:

1. Domain types.
2. Settings.
3. API request/response models.
4. API app with stubbed pipeline.
5. Stub detector/classifier/prior/taxonomy.
6. Image conversion.
7. Platform conversion adapters.
8. Detection plugin framework.
9. Grounding DINO plugin.
10. Deduplication.
11. Cropping.
12. Classifier plugin framework.
13. Birder classifier plugin.
14. Range prior service.
15. Logit conditioning.
16. Taxonomy service.
17. Multipart responses.
18. Startup pre-warming.
19. Performance instrumentation.
20. Production hardening.

---

## 27. Summary

Wild Catalog should be implemented as a clear, modular pipeline:

```text
API Gateway
→ Image Conversion Service
→ Detector Plugin
→ Deduplication Service
→ Cropping Service
→ Classifier Plugin
→ Species Range Prior Service
→ Logit Conditioning Layer
→ Taxonomy Service
→ API Response
```

The detector and classifier are runtime-selected plugins.

The range prior and taxonomy services are classifier-aware.

The API response uses `is_present`, not `is_endemic`.

HEIC/HEIF support is handled through optional platform conversion adapters, not
through `pillow-heif`.

The hot `/identify` path should use local models and local compiled data only. It
should not perform downloads, network calls, archive parsing, or expensive setup
work during request handling.

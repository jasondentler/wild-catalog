# System Architecture

Wild Catalog is organized as a small API gateway around a model-agnostic identification pipeline. The detector and classifier are runtime-selected plugins so the project can adopt better models over time without rewriting the API, image conversion, cropping, geographic conditioning, or taxonomy layers.

[Implementation Plan](./implementation-plan.md)

## Pipeline overview

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Gateway as API Gateway
    participant Status as Startup Status Tracker
    participant Converter as Image Conversion Service
    participant Detector as Detector Plugin
    participant DeDup as Duplicate Detection Service
    participant Cropper as Image Cropping Service
    participant Classifier as Classifier Plugin
    participant PriorServ as Species Range Prior Service
    participant Conditioner as Logit Conditioning Layer
    participant Taxonomy as Taxonomy Service

    User->>Gateway: Upload photo byte stream + JSON payload
    Gateway->>Status: Check readiness
    alt backend is still warming or failed
        Gateway-->>User: 503 Service Unavailable; call GET /status
    else backend is ready

    Gateway->>Converter: Pass raw photo stream and original filename
    activate Converter
    Note over Converter: Sniffs format, extracts metadata, optionally uses platform conversion, normalizes to RGB.
    Converter-->>Gateway: Return RGB image, metadata, and source format
    deactivate Converter

    Gateway->>Detector: Pass normalized RGB image
    activate Detector
    Note over Detector: Runtime-selected plugin. Default planned plugin: Grounding DINO with organism prompt.
    Detector-->>Gateway: Return normalized detections with xyxy pixel boxes, labels, categories, and confidence
    deactivate Detector

    Gateway->>DeDup: Pass detections
    activate DeDup
    Note over DeDup: Removes overlapping detections by category-aware IoU policy.
    DeDup-->>Gateway: Return filtered detections
    deactivate DeDup

    Gateway->>Cropper: Pass normalized image + filtered detections
    activate Cropper
    Cropper-->>Gateway: Return cropped RGB images with margin-aware boxes
    deactivate Cropper

    Gateway->>Classifier: Pass cropped RGB images
    activate Classifier
    Note over Classifier: Runtime-selected plugin. Prefer raw logits for downstream geographic conditioning.
    Classifier-->>Gateway: Return raw logits and classifier class-index metadata
    deactivate Classifier

    Gateway->>PriorServ: Fetch prior mask for GPS + classifier class index
    activate PriorServ
    Note over PriorServ: Classifier-aware SQLite/H3 prior lookup. Returns all-ones mask when GPS is missing.
    PriorServ-->>Gateway: Return spatial prior mask G of length N
    deactivate PriorServ

    Gateway->>Conditioner: Pass raw logits + prior mask
    activate Conditioner
    Note over Conditioner: Applies z_conditioned = z_raw + γ * log(G + ε), then Softmax.
    Conditioner-->>Gateway: Return top-k conditioned predictions
    deactivate Conditioner

    Gateway->>Taxonomy: Enrich class indices
    activate Taxonomy
    Note over Taxonomy: Uses active classifier class index to resolve taxonomy and common names, then attaches prior-supplied is_present flags.
    Taxonomy-->>Gateway: Return finalized species predictions
    deactivate Taxonomy

    Gateway-->>User: Return JSON or multipart/mixed response
    end
```

## Key architectural rules

1. The API gateway owns HTTP only.
2. The pipeline owns orchestration only.
3. Detector plugins own model-specific detection preprocessing, inference, and postprocessing.
4. Classifier plugins own model-specific crop preprocessing, inference, and class-index metadata; the pipeline depends on `SpeciesClassifier`, not concrete plugins such as Birder.
5. The range prior service must be aware of the active classifier class index.
6. The logit conditioning layer should operate on tensors and prior vectors only.
7. Taxonomy enrichment should use classifier class-index metadata rather than assuming one hard-coded taxonomy forever.
8. Platform image conversion is isolated inside the image conversion service.
9. Request-time range lookup reads WKB geometries from a local SQLite database
   through an RTree candidate query; downloading, parsing, and compiling raw
   range maps happens outside `/identify`.
10. Request-time taxonomy enrichment reads local taxonomy lookups only; it must
    not call live iNaturalist APIs or download `taxonomy.dwca.zip` during
    `/identify`.
11. The API gateway owns content negotiation and multipart response formatting.
    Pipeline and service layers return domain models and must not import
    FastAPI response classes or multipart helpers.
12. Startup uses FastAPI lifespan support to build one identify pipeline, warm required models and local stores, and store readiness state in `app.state`.
13. `GET /health` remains lightweight; `GET /status` reports startup readiness and pre-warming progress.
14. `POST /identify` must check readiness before expensive work and return `503 Service Unavailable` with a message that points clients to `GET /status` when the backend is not ready.


## Startup and readiness architecture

Wild Catalog uses FastAPI lifespan support to start the HTTP server quickly while a background startup warmup task prepares required dependencies. The default is eager preloading:

```text
WILD_CATALOG_PRELOAD_MODELS=true
```

During startup, the app should:

1. Build settings.
2. Build exactly one identify pipeline.
3. Store the pipeline in `app.state`.
4. Start warmup tasks for detector model, classifier model, taxonomy store, range prior store, and optional synthetic inference.
5. Track readiness in a thread-safe startup status tracker.

`GET /status` reads the startup status tracker and reports task states, progress, elapsed time, estimated time remaining, and failure details. `POST /identify` reads the same status tracker and refuses requests with `503 Service Unavailable` until the backend is ready. The 503 message must tell clients to call `GET /status`.

The warmed pipeline is the same pipeline used by `/identify`. Do not warm one pipeline and serve requests with another.

The startup package may depend on the pipeline because it is an application orchestration layer. The pipeline must not import startup or API modules.

## Components

1. [API Gateway](./api-gateway.md)
2. [Image Conversion Service](./image-conversion-service.md)
3. [Detection Service](./detection-service.md)
4. [Duplicate Detection Service](./deduplicate-detection-service.md)
5. [Image Cropping Service](./image-cropping-service.md)
6. [Species Classifier Service](./species-classifier-service.md)
7. [Species Range Prior Service](./species-range-prior-service.md)
8. [Logit Conditioning Layer](./logit-conditioning-layer.md)
9. [Taxonomy Service](./taxonomy-service.md)
10. [Deployment Guide](./deployments.md)

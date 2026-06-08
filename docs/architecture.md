# System Architecture

Wild Catalog is organized as a small API gateway around a model-agnostic identification pipeline. The detector and classifier are runtime-selected plugins so the project can adopt better models over time without rewriting the API, image conversion, cropping, geographic conditioning, or taxonomy layers.

[Implementation Plan](./implementation-plan.md)

## Pipeline overview

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Gateway as API Gateway
    participant Converter as Image Conversion Service
    participant Detector as Detector Plugin
    participant DeDup as Duplicate Detection Service
    participant Cropper as Image Cropping Service
    participant Classifier as Classifier Plugin
    participant PriorServ as Species Range Prior Service
    participant Conditioner as Logit Conditioning Layer
    participant Taxonomy as Taxonomy Service

    User->>Gateway: Upload photo byte stream + JSON payload

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
    Note over PriorServ: Classifier-aware prior lookup. Returns all-ones mask when GPS or compatible data is unavailable.
    PriorServ-->>Gateway: Return spatial prior mask G of length N
    deactivate PriorServ

    Gateway->>Conditioner: Pass raw logits + prior mask
    activate Conditioner
    Note over Conditioner: Applies z_conditioned = z_raw + γ * log(G + ε), then Softmax.
    Conditioner-->>Gateway: Return top-k conditioned predictions
    deactivate Conditioner

    Gateway->>Taxonomy: Enrich class indices
    activate Taxonomy
    Note over Taxonomy: Uses active classifier class index to resolve taxonomy, common names, and is_present flags.
    Taxonomy-->>Gateway: Return finalized species predictions
    deactivate Taxonomy

    Gateway-->>User: Return JSON or multipart/mixed response
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

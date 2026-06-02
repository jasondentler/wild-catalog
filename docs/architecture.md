# System Architecture

The following sequence diagram illustrates the internal processing pipeline for analyzing an uploaded photograph. It tracks the chronological flow of data through metadata extraction, detection, deduplication, cropping, model inference, and logit conditioning.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Gateway as API Gateway
    participant Converter as Image Conversion Service
    participant YOLO as YOLO Detection Service
    participant DeDup as Duplicate Detection Service
    participant Cropper as Image Cropping Service
    participant Classifier as Species Classifier Service
    participant PriorServ as Species Range Prior Service
    participant Conditioner as Logit Conditioning Layer
    participant Taxonomy as Taxonomy Language Service

    User->>Gateway: Upload photo byte stream (with implicit EXIF tags)

    Gateway->>Converter: Pass raw photo byte stream
    activate Converter
    Note over Converter: Normalizes image to RGB. Extracts EXIF file name & GPS.
    Converter-->>Gateway: Return Pillow-compatible RGB image, filename, & (lat, lon)
    deactivate Converter

    Gateway->>YOLO: Pass normalized photo
    activate YOLO
    YOLO-->>Gateway: Return raw bounding boxes (animals, plants, fungi)
    deactivate YOLO

    Gateway->>DeDup: Pass bounding boxes
    activate DeDup
    DeDup-->>Gateway: Return filtered boxes (overlapping duplicates removed)
    deactivate DeDup

    Gateway->>Cropper: Pass normalized photo + filtered boxes
    activate Cropper
    Cropper-->>Gateway: Return cropped images (inheriting RGB format)
    deactivate Cropper

    Gateway->>PriorServ: Fetch geographic prior mask G for (lat, lon)
    activate PriorServ
    Note over PriorServ: Maps GPS coordinates to iNaturalist Open Range Map grids
    PriorServ-->>Gateway: Return Spatial Prior Mask Vector (G) of length N
    deactivate PriorServ

    Gateway->>Classifier: Pass cropped RGB images
    activate Classifier
    Note over Classifier: Executes forward pass but stops before Softmax activation
    Classifier-->>Gateway: Return raw unconditioned leaf logits (z_raw)
    deactivate Classifier

    Gateway->>Conditioner: Pass raw logits (z_raw) + Prior Mask Vector (G)
    activate Conditioner
    Note over Conditioner: Applies additive log-space shift: z_conditioned = z_raw + γ * log(G + ε)
    Conditioner->>Conditioner: Compute Softmax probabilities on z_conditioned
    Conditioner-->>Gateway: Return species predictions
    deactivate Conditioner

    Gateway->>Taxonomy: Account for Taxonomy drift and look up common names
    activate Taxonomy
    Taxonomy-->>Gateway: Return finalized species predictions, including common names
    deactivate Taxonomy

    Gateway-->>User: Return finalized species identification results
```

## Components

1. [API Gateway](./api-gateway.md)
2. [Image Conversion Service](./image-conversion-service.md)
3. [YOLO Detection Service](./yolo-detection-service.md)
4. [DeDuplicate Detection Service](./deduplicate-detection-service.md)
5. [Image Cropping Service](./image-cropping-service.md)
6. [Species Classifier Service](./species-classifier-service.md)
7. [Species Range Prior Service](./species-range-prior-service.md)
8. [Logit Conditioning Layer](./logit-conditioning-layer.md)
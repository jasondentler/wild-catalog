# Identify Pipeline Layer

The identify pipeline coordinates the various stages to process an image and return predictions about the wildlife species in the image.

## Stages

The pipeline has the following stages:

1. [Image Conversion](stage-image-conversion.md)
2. [Wildlife Detection](stage-wildlife-detection.md)
3. [Detection Deduplication](stage-detection-deduplication.md)
4. Detection Processing Pipeline:
    1. [Detection Crop](stage-detection-crop.md)
    2. [Wildlife Classifier](stage-wildlife-classifier.md)
    3. [Species Range Logit Conditioning](stage-species-range-logit-conditioning.md)
    4. [Taxonomy Enrichment and Language Service](stage-taxonomy-enrichment.md)

## Pipeline Responsibility

The pipeline layer owns orchestration, not low-level decoding or HTTP concerns.

It is responsible for:

* streaming the uploaded bytes into the conversion stage
* carrying forward request metadata and overrides
* invoking downstream detection and classification work
* invoking the injected detection deduplication stage before object mapping
* returning a structured `IdentifyResult` for the API layer to serialize

## Inputs

The pipeline starts with an `IdentifyCommand`.

That command carries:

* the original filename, when known
* the uploaded size, when known
* optional EXIF overrides
* the `return_detected_images` preference
* the desired common-name language

## Outputs

The pipeline returns an `IdentifyResult` containing:

* zero or more identified objects
* optional GPS coordinates from EXIF metadata or request override, when known
* the `return_detected_images` flag that tells the API whether cropped images should be included in the response

The current implementation has the image conversion, wildlife detection, and detection deduplication stages wired. The API dependency layer assembles the concrete deduplicator and injects it into the pipeline constructor. The pipeline invokes the detector for converted images, passes the detections through that deduplication stage, and maps retained detections into response objects. Species classification, crop response population, and final detected-image payloads remain downstream implementation work.

## Design Boundary

This layer should remain free of:

* request parsing
* HTTP headers
* OpenAPI concerns
* multipart handling

That keeps the pipeline reusable from the API layer and easier to test in isolation.

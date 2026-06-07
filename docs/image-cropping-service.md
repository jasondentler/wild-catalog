[Architecture](./architecture.md)

# Image Cropping Service

## Responsibility

The image cropping service isolates each deduplicated target into an RGB crop for species classification. It provides enough surrounding context to preserve diagnostic features such as wings, tails, flower petals, leaves, stems, fungal caps, or lichen edges.

## Technical Stack

* `Pillow`

## Operation: `extract_target_regions`

### Description

The service loops through deduplicated detections, calculates a margin around each detection box, clamps that margin to image boundaries, and returns crop records.

The cropper does not know which detector plugin produced the box. It only needs normalized pixel coordinates.

### Inputs

* `normalized_image`: Complete source image in RGB mode.
* `filtered_detections`: Deduplicated `Detection` objects.
* `margin_ratio`: Configured padding ratio.

### Outputs

* `cropped_images`: Ordered RGB crop images.
* `bounding_box`: Original detection box.
* `bounding_box_with_margin`: Padded and clamped crop box.

## Recommended internal model

```python
@dataclass(frozen=True, slots=True)
class CropResult:
    index: int
    detection: Detection
    bounding_box: BoundingBox
    bounding_box_with_margin: BoundingBox
    image: Image.Image
```

## Memory rules

* Crop only after deduplication.
* Cap detections before cropping.
* Keep crops in RGB mode.
* Do not encode crop images unless `return_detected_images=true`.
* Release crop images after classification and response serialization.

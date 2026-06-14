# Wildlife Detection Pipeline Stage

The wildlife detection stage of the identify pipeline is responsible for identifying candidate subjects in the converted image and preparing them for classification.

In the `POST /identify` pipeline, this step is preceded by the image conversion layer and followed by the classification and response mapping work.

## Responsibilities

The detection stage should stay focused on localizing subjects.

It is responsible for:

1. Inspecting the normalized RGB image from the conversion stage.
2. Finding candidate wildlife regions.
3. Returning broad candidate detections for downstream deduplication, crop, and classification stages.

It currently returns project `Detection` objects containing:

* a pixel-space `BoundingBox`
* a confidence score from `0.0` to `1.0`
* a broad detector class id
* an optional broad label such as `animal`, `person`, or `vehicle`

## Implementation

The default detector is `WildlifeDetector`, an alias for `MegaDetectorV6Detector`.

`MegaDetectorV6Detector` is an adapter around PyTorch-Wildlife MegaDetector v6. It prefers the Apache RT-DETR implementation exposed by PyTorch-Wildlife as `MegaDetectorV6Apache`, using the `MDV6-apa-rtdetr-e` model version by default.

The detector implementation is behind the `Detector` interface so a different localization backend can be swapped in without changing the identify pipeline.

The detector package is split by responsibility:

* `detector_base.py`: detector interface
* `mega_detector_v6_detector.py`: PyTorch-Wildlife adapter and result mapping
* `megadetector_factory.py`: PyTorch-Wildlife model selection
* `optional_dependency_stubs.py`: import compatibility for unused optional PyTorch-Wildlife modules
* `torch_hub_cache.py`: local Torch Hub cache configuration
* `pytorch_wildlife_stdout.py`: suppression for one noisy third-party model-load print

## Input and Output

The stage receives a decoded RGB `PIL.Image` from the conversion layer.

It produces zero or more broad detections. It does not produce classifier predictions or final API response objects.

The current pipeline invokes the detector and keeps the stage boundary in place, but final response mapping from detections to identified species remains downstream work.

## Model Assets

The default model path used by tests and local workflows is:

```text
models/MDV6-apa-rtdetr-e.pth
```

If no explicit model weights are supplied, PyTorch-Wildlife may download its configured weights. The Apache RT-DETR implementation may also use Torch Hub to fetch an RT-DETR backbone checkpoint on first model construction.

When `TORCH_HOME` is not set, Wild Catalog points Torch Hub at:

```text
models/torch-hub
```

That keeps generated detector assets under the project workspace instead of the user-level Torch cache.

## Boundary With Other Stages

The detection stage does not own:

* file format sniffing
* EXIF parsing
* upload size validation
* crop-margin calculation
* species classification
* response serialization

Those belong to the conversion and API layers.

The detection stage also should not decide how responses are formatted for clients.
That behavior is handled later by the API layer's content negotiation and response mapper.

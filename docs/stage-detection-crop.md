# Detection Crop

The detection crop stage extracts an image region around a detected object and records both the original detection bounding box and the padded crop bounding box.

## Crop Margin Settings

Crop padding is controlled by application settings:

* `crop_margin_ratio`: proportional padding based on the detection box size. Defaults to `0.10`.
* `crop_margin_min_px`: minimum padding in pixels. Defaults to `8`.

These settings can be overridden with environment variables:

```text
WILD_CATALOG_CROP_MARGIN_RATIO=0.10
WILD_CATALOG_CROP_MARGIN_MIN_PX=8
```

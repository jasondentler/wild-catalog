[Architecture](./architecture.md)

# Image Conversion Service

## Responsibility

The image conversion service ingests blind binary image streams, extracts useful metadata, optionally delegates unsupported platform-native formats to an operating-system conversion adapter, and normalizes images to a single RGB layout for downstream detector and classifier plugins.

The rest of the pipeline should not know whether the source image started as JPEG, PNG, or another supported format. Downstream services receive a normalized RGB Pillow image plus metadata.

## Technical Stack

Core Python dependencies:

* `Pillow`
* `rawpy`
* `exifread`

Explicitly excluded dependencies:

* `pillow-heif`
* direct native Python HEIC/HEIF decoding libraries

## Operation: `process_and_extract_metadata`

### Description

The service reads the incoming file stream, enforces configured size limits, sniffs the format, extracts metadata, and returns an RGB image.

Standard image formats such as JPEG, PNG, and WebP are processed through Pillow. RAW formats are decoded through `rawpy` when supported by the installed runtime.

### Inputs

* `file_stream`: Raw uploaded binary stream.
* `original_filename`: Client-provided filename used for diagnostics and extension hints only.
* `exif_override`: Optional request metadata that may override embedded metadata later in the pipeline.

### Outputs

* `normalized_image`: Pillow `Image` in RGB mode.
* `original_filename_from_exif`: Source filename from EXIF if available.
* `gps_coordinates`: Decimal `(latitude, longitude)` tuple or `None`.
* `captured_at`: Capture timestamp or `None`.

## Metadata precedence

The pipeline should apply metadata in this order:

1. Request `exif_override` values.
2. Metadata extracted from the original upload.
3. `None`.

## Memory constraints

* Do not keep multiple decoded full-resolution images alive.
* Stream or spool uploads rather than duplicating large byte arrays where possible.
* Convert to RGB once.
* Close temporary Pillow images promptly.

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

The service reads the incoming file stream, enforces configured size limits, sniffs the format, extracts metadata, and returns an RGB image with normalized metadata.

JPEG, PNG, and WebP are processed directly through Pillow. RAW formats are decoded through `rawpy` when supported by the installed runtime. HEIC and HEIF are supported only through optional platform conversion adapters, then decoded through the normal JPEG path.

### Inputs

* `image_file`: Raw uploaded binary stream.
* `original_filename`: Client-provided filename used for diagnostics and extension hints only.
* `gps_coordinates_override`: Optional GPS override from the request.
* `captured_at_override`: Optional capture-time override from the request.

### Outputs

* `image`: Pillow `Image` in RGB mode.
* `original_filename`: Source filename from metadata if available, otherwise the client-provided filename.
* `gps_coordinates`: Decimal latitude and longitude or `None`.
* `captured_at`: Capture timestamp or `None`.
* `detected_format`: Stable internal format string such as `jpeg`, `heic`, or `cr3`.

## Supported formats

* JPEG, PNG, and WebP are decoded directly with Pillow.
* RAW files are routed through `rawpy`; actual support depends on the installed LibRaw runtime.
* HEIC and HEIF are not decoded by Python HEIC libraries. They require an optional platform converter such as macOS `sips` or ImageMagick with HEIC support.
* Platform converters automatically resolve their external utility from `PATH` or the platform default location before reporting that they can convert a format.
* Platform converters must call external commands with argument lists and timeouts, never `shell=True`.

## Metadata precedence

The conversion service applies metadata in this order:

1. Request `exif_override` values.
2. Metadata extracted from the original upload.
3. `None`.

## Memory constraints

* Do not keep multiple decoded full-resolution images alive.
* Stream or spool uploads rather than duplicating large byte arrays where possible.
* Convert to RGB once.
* Close temporary Pillow images promptly.

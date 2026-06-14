# Image Conversion

The image conversion stage is the first concrete processing step in the identify pipeline.
Its job is to take uploaded bytes, identify the image format, decode the image into a standard RGB `PIL.Image`, and extract any EXIF metadata that can be used later in the pipeline.

This stage is implemented by `ImageConversionService`.

## Responsibilities

The conversion stage does four things:

1. Reads the uploaded file into memory.
2. Enforces the upload size limit before any decode work begins.
3. Detects the image format and selects the correct converter strategy.
4. Decodes the image and extracts metadata from the original bytes.

The service returns a `ConvertedImage` object containing:

- the decoded RGB image
- the detected file format
- the original filename
- GPS coordinates, if available
- capture timestamp, if available

## Flow

The service follows this sequence:

1. Read the upload bytes from the incoming `BinaryIO`.
2. Reject the upload if it exceeds `max_upload_bytes`.
3. Detect the file format with `sniff_image_format()`.
4. Extract EXIF metadata with `extract_metadata()`.
5. Select an image converter through `build_format_sniffer_chain()`.
6. Convert the bytes to an RGB image.
7. Check the decoded image dimensions against `max_image_pixels`.
8. Return the converted image plus metadata.

The service keeps the invariant checks at the boundary:

- upload size is validated before decode
- decoded pixel count is validated after decode

That keeps the converters focused on decoding only.

## Converter Strategy

The conversion layer uses a Gang of Four strategy pattern.

The format sniffer chain acts as the selector:

- `RawFormatSniffer` handles RAW filename extensions
- `JpegFormatSniffer` handles JPEG magic bytes
- `PngFormatSniffer` handles PNG magic bytes
- `WebPFormatSniffer` handles WebP magic bytes
- `HeicFormatSniffer` and `HeifFormatSniffer` reject unsupported HEIC/HEIF payloads
- `NotSupportedSniffer` raises when nothing matches

Each matching sniffer returns a converter instance.

The converters themselves do one thing:

- `PillowConverter` decodes standard image formats and applies EXIF orientation
- `RawConverter` decodes RAW files through `rawpy`

The service then validates the final image size and returns the decoded image.

## Metadata Extraction

EXIF metadata is extracted from the original upload bytes before decoding.

This is separate from image conversion because:

- some metadata exists even when the image cannot be decoded later
- EXIF reading should not depend on the selected converter
- the metadata is needed for downstream pipeline overrides

The extracted metadata currently includes:

- original filename, if embedded
- GPS coordinates
- capture timestamp

## Supported Formats

The stage currently supports:

- JPEG
- PNG
- WebP
- RAW extensions such as `cr3`, `dng`, and related camera formats

HEIC and HEIF are detected but intentionally rejected with `UnsupportedImageFormatError`.

## Error Handling

The conversion stage raises specific failures for predictable failure modes:

- `ImageTooLargeError` when the upload exceeds the byte limit or the decoded image exceeds the pixel limit
- `UnsupportedImageFormatError` when the file type is unsupported
- `InvalidImageError` when a supported format cannot be decoded

These errors are handled by the API layer and translated into the project’s standard error response shape.

## Design Notes

The important design boundary is that converters should stay simple.

They should decode bytes into images.

They should not know about request context, upload size limits, or pipeline-specific policy.

Those checks belong to `ImageConversionService`, which owns the conversion policy for the identify pipeline.

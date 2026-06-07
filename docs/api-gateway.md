[Architecture](./architecture.md)

# API Gateway

The API gateway exposes the public HTTP contract for Wild Catalog. It should own HTTP parsing, request validation, content negotiation, response formatting, and error mapping. It should not contain image conversion, model inference, crop, range-prior, taxonomy, or logit-conditioning logic.

## Endpoints

* `GET /health`
* `GET /openapi.json`
* `GET /docs`
* `POST /identify`

## `GET /health`

The health endpoint returns a lightweight service status for deployment checks, load balancers, and smoke tests. It does not run the image identification pipeline and does not verify that detector models, classifier models, taxonomy data, or spatial range-prior data have been loaded.

### Response Example

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "status": "ok"
}
```

## `GET /openapi.json`

FastAPI serves the generated OpenAPI document at `GET /openapi.json`. This endpoint is useful for client generation, API inspection, and automated contract checks.

### Response Reference

* **200 OK**: Returns the generated OpenAPI JSON document.
* **Content-Type**: `application/json`

## `GET /docs`

FastAPI serves the interactive Swagger UI documentation at `GET /docs`. This endpoint provides a user-friendly browser interface for developers to inspect endpoints, review request/response schemas, and interactively test the API contracts.

### Dependencies & Network Requirements
To render the interface, the browser client must have outbound public internet access to fetch the following external static assets:
*   **CSS**: `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css`
*   **JS**: `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js`

### Access Control
*   **Visibility**: Publicly accessible.
*   **Authentication**: None required to view the documentation interface.

### Response Reference
*   **200 OK**: Returns the rendered HTML document containing the Swagger UI application.
*   **Content-Type**: `text/html; charset=utf-8`

## `POST /identify`

The API gateway's primary endpoint is `POST /identify`. It accepts a `multipart/form-data` request with two parts:

1. The image to be processed.
2. A JSON request payload.

### Supported input formats

Wild Catalog should process these formats directly in the Python image stack:

* JPEG / JPG
* PNG
* WebP
* RAW image formats supported by the configured `rawpy` runtime, including common camera RAW formats such as `.dng`, `.cr3`, `.cr2`, `.nef`, `.arw`, `.orf`, `.rw2`, `.raf`, `.pef`, and similar formats.

Note: Due to patent and license concerns, HEIC / HEIF is not supported at this time.

### JSON Request Payload Reference

The request body must include a JSON object containing information about the media upload, metadata overrides, and processing preferences.

#### Property Details

* `original_filename` (string, **required**): The original client-visible file name.
* `exif_override` (object, optional): Metadata values to supplement or replace the file's original metadata.
  * `gps_coordinates` (string): Latitude and longitude separated by a comma, using floating-point notation.
  * `captured_at` (string): Date and time the photo was taken, using ISO 8601 format.
* `return_detected_images` (boolean, optional): Set to `true` to include cropped images of detected subjects in the response. Defaults to `false`.
* `common_name_language` (string, optional): Locale code for returned common names. Defaults to `en-US`.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org",
  "title": "MediaUploadPayload",
  "type": "object",
  "properties": {
    "original_filename": {
      "type": "string"
    },
    "exif_override": {
      "type": "object",
      "properties": {
        "gps_coordinates": {
          "type": "string",
          "pattern": "^-?\\d+\\.\\d+,\\s*-?\\d+\\.\\d+$"
        },
        "captured_at": {
          "type": "string",
          "format": "date-time"
        }
      }
    },
    "return_detected_images": {
      "type": "boolean",
      "default": false
    },
    "common_name_language": {
      "type": "string",
      "default": "en-US"
    }
  },
  "required": ["original_filename"]
}
```

### Request Example

```json
{
  "original_filename": "dsc_0432.jpg",
  "exif_override": {
    "gps_coordinates": "37.7749,-122.4194",
    "captured_at": "2026-06-02T05:39:00Z"
  },
  "return_detected_images": true,
  "common_name_language": "es-MX"
}
```

## Response Reference

### HTTP Status Codes

* **200 OK**: Processing completed successfully.
* **400 Bad Request**: Malformed JSON payload, invalid GPS override, or invalid request shape.
* **413 Payload Too Large**: Uploaded file or decoded image exceeds configured size limits.
* **415 Unsupported Media Type**: Unsupported file type or unavailable platform conversion adapter.
* **422 Unprocessable Entity**: Image appears supported but cannot be decoded or converted.
* **503 Service Unavailable**: Required model or data store is unavailable.

### Content-Type Behavior

If `return_detected_images` is `true`, the API forces `multipart/mixed`. The first part is always the JSON payload, followed by image parts containing cropped subject JPEGs with margin applied.

If `return_detected_images` is `false`, the API honors the client's `Accept` header:

* `application/json`: Returns only the JSON payload. This is the default if no `Accept` header is provided.
* `multipart/mixed`: Returns a multipart package containing only the JSON payload part.

### Response Property Details

The root JSON response payload is an array of zero or more detected object structures.

* `bounding_box` (object): Exact detected boundary in the original normalized image.
  * `xmin`, `ymin`, `xmax`, `ymax`, `height`, `width`.
* `bounding_box_with_margin` (object): Padded crop boundary after margin/clamping.
  * `xmin`, `ymin`, `xmax`, `ymax`, `height`, `width`.
* `gps_coordinates` (array of two numbers / null): Decimal latitude and longitude used for the identification request after EXIF overrides.
* `predictions` (array): Classification hypotheses for the bounding box.
  * `confidence` (number): Prediction probability from `0.0` to `1.0` after optional logit conditioning.
  * `is_present` (boolean): Indicates whether the predicted species is present at the provided GPS coordinates when that data is available.
  * `taxonomy` (array of strings): Scientific taxonomic lineage ordered from highest rank to lowest rank.
  * `taxonomy_common_names` (array of strings): Localized common names matching the equivalent rank index in `taxonomy`.

### Response Example: `application/json`

```json
[
  {
    "bounding_box": {
      "xmin": 120,
      "ymin": 340,
      "xmax": 450,
      "ymax": 680,
      "width": 330,
      "height": 340
    },
    "bounding_box_with_margin": {
      "xmin": 100,
      "ymin": 320,
      "xmax": 470,
      "ymax": 700,
      "width": 370,
      "height": 380
    },
    "gps_coordinates": [37.7749, -122.4194],
    "predictions": [
      {
        "confidence": 0.982,
        "is_present": true,
        "taxonomy": [
          "Animalia",
          "Chordata",
          "Aves",
          "Passeriformes",
          "Corvidae",
          "Cyanocitta",
          "Cyanocitta cristata"
        ],
        "taxonomy_common_names": [
          "Animals",
          "Chordates",
          "Birds",
          "Perching Birds",
          "Crows and Jays",
          "Blue Jays",
          "Blue Jay"
        ]
      }
    ]
  }
]
```

### Response Example: `multipart/mixed`

```http
HTTP/1.1 200 OK
Content-Type: multipart/mixed; boundary=detection_boundary

--detection_boundary
Content-Type: application/json

[
  {
    "bounding_box": {
      "xmin": 120,
      "ymin": 340,
      "xmax": 450,
      "ymax": 680,
      "width": 330,
      "height": 340
    },
    "bounding_box_with_margin": {
      "xmin": 100,
      "ymin": 320,
      "xmax": 470,
      "ymax": 700,
      "width": 370,
      "height": 380
    },
    "gps_coordinates": [37.7749, -122.4194],
    "predictions": []
  }
]
--detection_boundary
Content-Type: image/jpeg
Content-Disposition: attachment; filename="detection_1.jpg"

[... Binary JPEG Data for the Crop with Margin ...]
--detection_boundary--
```

JSON responses may omit pretty-printing whitespace in production.

# API Layer

The API layer has the following endpoints:

* `GET /health`
* `GET /openapi.json`
* `POST /identify`

## GET /health

The health endpoint returns a lightweight service status for deployment checks,
load balancers, and smoke tests. It does not run the image identification
pipeline or verify that ML models and spatial data have been loaded.

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

## GET /openapi.json

FastAPI serves the generated OpenAPI document at `GET /openapi.json`. This
endpoint is useful for client generation, API inspection, and automated contract
checks.

### Response Reference

#### HTTP Status Codes

* **200 OK**: Returns the generated OpenAPI JSON document.

#### Response Content-Type

* `application/json`

## POST /identify

The API gateway's primary endpoint is `POST /identify`.

Send an image to be processed in one of two request shapes:

* Direct upload: send the image bytes in the request body.
* Multipart upload: send `multipart/form-data` with an `image` part and an optional `payload` part containing JSON.

Supported direct upload formats:

* Standard image formats handled by Pillow:
  * JPEG / JPG: `Content-Type: image/jpeg`
  * PNG: `Content-Type: image/png`
  * WebP: `Content-Type: image/webp`
* RAW image formats handled by `rawpy`:
  * Use `Content-Type: application/octet-stream`
  * Adobe Digital Negative (`.dng`)
  * Canon: `.cr3`, `.cr2`, `.crw`
  * DJI: `.dng`
  * Fujifilm: `.raf`
  * GoPro: `.gpr`
  * Hasselblad: `.3fr`, `.fff`
  * Kodak: `.dcr`, `.k25`, `.kdc`
  * Leaf: `.mos`
  * Nikon: `.nef`, `.nrw`
  * OM System / Olympus: `.orf`
  * Panasonic / Lumix: `.rw2`
  * Pentax: `.pef`
  * Sony: `.arw`, `.srf`, `.sr2`
  * Phase One: `.iiq`

For direct image uploads, also include:

* `x-filename` (optional): the original filename to use if the upload is not multipart. If omitted, the server will fall back to the multipart filename when available or leave it unset.
* `content-language`: optional fallback language for common names
* `content-length`: required for `POST`, `PUT`, and `PATCH` requests so the upload size limiter can reject oversized requests before image parsing begins

`content-language` accepts a language tag or comma-separated weighted list. The highest-weight tag is used when no `common_name_language` is supplied in the multipart payload.

You may also send a `multipart/form-data` request containing these parts:

1. an image as above
2. an optional `payload` form field containing JSON

### Payload Size Limit Middleware

`POST /identify` is protected by an HTTP middleware that checks the request
`Content-Length` header before the request body is handed to the route handler.
This keeps oversized uploads out of the image parsing and conversion path.

The limit is configured by `WILD_CATALOG_MAX_UPLOAD_BYTES`. If the environment
variable is not set, the default is `100000000` bytes.

The middleware applies to `POST`, `PUT`, and `PATCH` requests. It does not run
for methods that normally do not carry a request body, such as `GET`.

#### Middleware Rejections

* Missing `Content-Length`: rejected as `400 Bad Request`.
* Non-numeric `Content-Length`: rejected as `400 Bad Request`.
* `Content-Length` greater than `WILD_CATALOG_MAX_UPLOAD_BYTES`: rejected as `413 Payload Too Large`.

The middleware checks only the declared `Content-Length` value. It does not
perform content negotiation or image format detection; those remain downstream
API and conversion concerns.

### JSON Request Payload Reference

The request body must be a JSON object containing information about the media upload, metadata overrides, and processing preferences.

#### Property Details

* `original_filename` (string, required): The exact name of the uploaded file.
* `exif_override` (object, optional): Metadata values to supplement or replace the file's original data.
  * `gps_coordinates` (string, optional): Latitude and longitude separated by a comma.
  * `captured_at` (string, optional): The date and time the photo was taken in ISO 8601 format.
* `return_detected_images` (boolean, optional): Set to `true` to include cropped images of detected subjects in the response. Defaults to `false`.
* `common_name_language` (string, optional): Locale code for returned common names. Defaults to `en-US`.

---

### JSON Schema

```json
{
  "\$schema": "https://json-schema.org",
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
          "pattern": "^-?\\d+\\.\\d+,\\s*-?\\d+\\.\\d+\$"
        },
        "captured_at": {
          "type": "string",
          "format": "date-time"
        }
      },
      "required": ["gps_coordinates", "captured_at"]
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

Note: the JSON schema above mirrors the example payload shape used in the OpenAPI document. In practice, `original_filename` is required when the JSON payload is provided, but direct uploads can also supply the filename through `x-filename` or multipart filename metadata.

---

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

### Response Reference

#### HTTP Status Codes
*   **200 OK**: Processing completed successfully. Returns data according to the request configuration.

#### Response Content-Type Behavior
* If `return_detected_images` is `true`: the API returns `multipart/mixed` when the client's `Accept` header allows it. The first part is always the JSON payload, followed by cropped JPEG image parts when available.
* If `return_detected_images` is `false`: the API honors the client's `Accept` header.
  * `application/json`: Returns only the JSON payload. This is the default when `Accept` is absent.
  * `multipart/mixed`: Returns a multipart package containing only the JSON payload part.

---

### Response Property Details (JSON Payload)

The root response payload is a JSON array of zero or more detected object structures.

* `bounding_box` (object): Coordinates for the exact entity boundary in the original image.
  * `xmin`, `ymin`, `xmax`, `ymax`, `height`, `width` (integer): Pixel coordinates and dimensions.
* `bounding_box_with_margin` (object): Coordinates for the boundary after margin padding is applied.
  * `xmin`, `ymin`, `xmax`, `ymax`, `height`, `width` (integer): Pixel coordinates and dimensions.
* `gps_coordinates` (array of two numbers or null): Decimal latitude and longitude used for the request, after applying any EXIF override.
* `predictions` (array): Classification hypotheses for the bounding box.
  * `confidence` (number): Prediction score from `0.0` to `1.0`.
  * `is_present` (boolean): Indicates whether the prediction is considered present.
  * `taxonomy` (array of strings): Scientific taxonomic lineage ordered from highest rank to lowest rank.
  * `taxonomy_common_names` (array of strings): Localized common names matching the taxonomy ranks.

---

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
      },
      {
        "confidence": 0.015,
        "is_present": true,
        "taxonomy": [
          "Animalia",
          "Chordata",
          "Aves",
          "Passeriformes",
          "Mimidae",
          "Mimus",
          "Mimus polyglottos"
        ],
        "taxonomy_common_names": [
          "Animals",
          "Chordates",
          "Birds",
          "Perching Birds",
          "Mockingbirds and Thrashers",
          "Northern Mockingbirds",
          "Northern Mockingbird"
        ]
      }
    ]
  }
]
```

---

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
      },
      {
        "confidence": 0.015,
        "is_present": true,
        "taxonomy": [
          "Animalia",
          "Chordata",
          "Aves",
          "Passeriformes",
          "Mimidae",
          "Mimus",
          "Mimus polyglottos"
        ],
        "taxonomy_common_names": [
          "Animals",
          "Chordates",
          "Birds",
          "Perching Birds",
          "Mockingbirds and Thrashers",
          "Northern Mockingbirds",
          "Northern Mockingbird"
        ]
      }
    ]
  }
]
--detection_boundary
Content-Type: image/jpeg
Content-Disposition: attachment; filename="detection_1.jpg"

[... Binary JPEG Data for the Crop with Margin ...]
--detection_boundary--
```

___Note:___ The JSON responses above were pretty-printed. Whitespace may be omitted in the actual HTTP response. 

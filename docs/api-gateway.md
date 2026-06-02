[Architecture](./architecture.md)

# API Gateway

The API gateway has the following endpoints:

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

The API gateway's primary endpoint is `POST /identify`. It accepts a multipart form data payload with two parts:
1. The image to be processed, in any of these formats:

    * Standard image formats for `pillow`:
        * JPEG / JPG, 
        * PNG
        * WebP
        * HEIF
        * HEIC (Apple iPhone & iPad)
    * RAW image formats using `rawpy`:
        * Adobe Digital Negative (`.dng`)
        * Canon: `.cr3` (newer bodies like EOS R series), `.cr2`, `.crw` (legacy bodies)
        * dji: `.dng`
        * Fujifilm: `.raf` (including their unique X-Trans and GFX sensor formats).
        * GoPro: `.gpr`
        * Hasselblad: `.3fr`, `.fff`
        * Kodak: `.dcr`, `.k25`, `.kdc`
        * Leaf: `.mos`
        * Nikon: `.nef`, `.nrw` (high-end compact coolpix lines)
        * OM System / Olympus: `.orf`
        * Panasonic / Lumix: `.rw2`
        * Pentax: `.pef`
        * Sony: `.arw`, `.srf`, `.sr2`
        * Phase One: `.iiq`
2. A JSON request payload

### JSON Request Payload Reference

The request body must be a JSON object containing information about the media upload, metadata overrides, and processing preferences.

#### Property Details

*   `original_filename` (string, **required**): The exact name of the uploaded file.
*   `exif_override` (object, optional): Metadata values to supplement or replace the file's original data.
    *   `gps_coordinates` (string): Latitude and longitude separated by a comma. Uses floating-point notation. 
    *   `captured_at` (string): The date and time the photo was taken. Must use ISO 8601 format.
*   `return_detected_images` (boolean, optional): Set to `true` to include cropped images of detected subjects in the response. Defaults to `false`.
*   `common_name_language` (string, optional): Specifies the language locale code for the returned common names of organisms. Defaults to `en-US`.

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
*   **If `return_detected_images` is `true`**: The API forces a Content-Type of `multipart/mixed`. The first part is always the JSON payload, followed by subsequent parts containing the cropped binary image files (with margins applied).
*   **If `return_detected_images` is `false`**: The API honors the client's `Accept` header.
    *   `application/json`: Returns only the JSON payload. (Default if no `Accept` header is provided).
    *   `multipart/mixed`: Returns a multipart package containing only the JSON payload part.

---

### Response Property Details (JSON Payload)

The root response payload is a JSON array of zero or more detected object structures.

*   `bounding_box` (object): Coordinates detailing the exact boundary of the entity in the original image.
    *   `xmin` / `ymin` / `xmax` / `ymax` / `height` / `width` (integer): Pixel coordinates of the crop boundaries + height and width.
*   `bounding_box_with_margin` (object): Coordinates detailing the boundary with extra margin padding applied.
    *   `xmin` / `ymin` / `xmax` / `ymax` / `height` / `width` (integer): Pixel coordinates of the padded crop boundaries + height and width.
*   `gps_coordinates` (array of two numbers / null): Decimal latitude and longitude used for the identification request, after applying any EXIF override.
*   `predictions` (array): A list of classification hypotheses for the specific bounding box.
    *   `confidence` (number): Prediction probability score ranging from `0.0` to `1.0`.
    *   `is_endemic` (boolean): Flag indicating if the predicted species is endemic to the provided GPS coordinates.
    *   `taxonomy` (array of strings): The complete scientific taxonomic lineage ordered from highest rank to lowest rank (e.g., Kingdom down to Species).
    *   `taxonomy_common_names` (array of strings): The localized common names matching each equivalent rank index in the `taxonomy` array, localized to the requested language. Birder-backed predictions resolve these names from the iNaturalist Taxonomy DarwinCore Archive.

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
        "is_endemic": true,
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
        "is_endemic": true,
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
        "is_endemic": true,
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
        "is_endemic": true,
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

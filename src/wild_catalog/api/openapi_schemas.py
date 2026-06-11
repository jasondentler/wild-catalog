from __future__ import annotations

import json

IDENTIFY_PAYLOAD_EXAMPLE = {
    "original_filename": "IMG_7906.jpg",
    "exif_override": {
        "gps_coordinates": "29.573361, -94.389507",
        "captured_at": "2026-05-01T12:30:00Z",
    },
    "return_detected_images": True,
    "common_name_language": "en-US",
}

IDENTIFY_PAYLOAD_EXAMPLE_JSON = json.dumps(IDENTIFY_PAYLOAD_EXAMPLE)

IDENTIFY_REQUEST_OPENAPI_EXTRA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["image"],
                    "properties": {
                        "image": {
                            "type": "string",
                            "format": "binary",
                            "description": "Image file upload.",
                        },
                        "payload": {
                            "type": "object",
                            "description": "Optional JSON payload as a string.",
                            "example": IDENTIFY_PAYLOAD_EXAMPLE,
                        },
                    },
                },
                "encoding": {
                    "payload": {
                        "contentType": "application/json"
                    }
                },
                "examples": {
                    "imageOnly": {
                        "summary": "Image only",
                        "value": {
                            "image": "<binary image file>",
                        },
                    },
                    "imageAndPayload": {
                        "summary": "Image and JSON payload",
                        "value": {
                            "image": "<binary image file>",
                            "payload": IDENTIFY_PAYLOAD_EXAMPLE,
                        },
                    },
                },
            },
            "application/octet-stream": {
                "schema": {
                    "type": "string",
                    "format": "binary",
                },
                "examples": {
                    "rawImage": {
                        "summary": "Raw bytes upload",
                        "value": "<binary image bytes>",
                    }
                },
            },
            "image/jpeg": {
                "schema": {
                    "type": "string",
                    "format": "binary",
                },
                "examples": {
                    "rawImage": {
                        "summary": "JPEG upload",
                        "value": "<binary image bytes>",
                    }
                },
            },
        },
    }
}

# Curl Commands

This document collects `curl` commands for exercising `POST /identify` with the sample images in `sample-images/` and other scenarios.

## Files Used

* `sample-images/20260402-IMG_7906.jpg`
* `sample-images/20260419-DA8A0090.jpg`
* `sample-images/20260419-DA8A5083.jpg`
* `sample-images/20260419-DA8A5151.jpg`
* `sample-images/20260419-DA8A5506.jpg`
* `sample-images/20260419-DA8A7718.jpg`
* `sample-images/20260402-IMG_7906.png`
* `sample-images/20260402-IMG_7906.webp`
* `sample-images/20260525-IMG_7906.heic`
* `sample-images/20260525-IMG_7906.CR3`
* `sample-images/20260525-IMG_7906.dng`
* `sample-images/20260525-IMG_7906_1.dng`

Assume the API is running at `http://127.0.0.1:8000`.

## Direct JPEG Upload

Use this for the standard direct upload path.
The shell script prints a short scenario label before running the request.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: image/jpeg' \
  -H 'x-filename: 20260402-IMG_7906.jpg' \
  --data-binary '@sample-images/20260402-IMG_7906.jpg'
```

## Direct PNG Upload

Use this for a direct `image/png` upload.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: image/png' \
  -H 'x-filename: 20260402-IMG_7906.png' \
  --data-binary '@sample-images/20260402-IMG_7906.png'
```

## Direct WebP Upload

Use this for a direct `image/webp` upload.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: image/webp' \
  -H 'x-filename: 20260402-IMG_7906.webp' \
  --data-binary '@sample-images/20260402-IMG_7906.webp'
```

## Multipart JPEG Upload

Use this when sending an image as `multipart/form-data` without a JSON payload.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -F 'image=@sample-images/20260402-IMG_7906.jpg;type=image/jpeg'
```

## Multipart JPEG Upload With Payload

Use this when you want to supply request metadata alongside the upload and request cropped images.
The shell script prints `Multipart JPEG upload with payload` before issuing the request.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: multipart/mixed' \
  -F 'image=@sample-images/20260402-IMG_7906.jpg;type=image/jpeg' \
  -F 'payload={"original_filename":"override-name.jpg","return_detected_images":true,"common_name_language":"es-MX"};type=application/json'
```

## Multipart JPEG Upload Without Payload

Use this for the simplest multipart flow.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -F 'image=@sample-images/20260402-IMG_7906.jpg;type=image/jpeg'
```

## Direct RAW Upload

Use this for RAW files that the service supports by filename, such as CR3 or DNG.
The CR3 sample is a supported RAW path in this repository, and the DNG samples provide additional RAW coverage.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/octet-stream' \
  -H 'x-filename: 20260525-IMG_7906.CR3' \
  --data-binary '@sample-images/20260525-IMG_7906.CR3'
```

## Direct DNG Upload

Use this for a direct RAW upload using a DNG file.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/octet-stream' \
  -H 'x-filename: 20260525-IMG_7906.dng' \
  --data-binary '@sample-images/20260525-IMG_7906.dng'
```

## Direct DNG Upload 2

Use this for the second DNG sample file.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/octet-stream' \
  -H 'x-filename: 20260525-IMG_7906_1.dng' \
  --data-binary '@sample-images/20260525-IMG_7906_1.dng'
```

## Oversized Payload Upload

Use this to verify the content-length limiter rejects payloads that exceed the configured upload size.
The example writes a temporary payload file so `curl` sends a real `Content-Length` header.
The shell script prints `Oversized payload upload to test the content-length limiter` before sending the request.
By default the generated payload is one byte larger than `WILD_CATALOG_MAX_UPLOAD_BYTES` if that environment variable is set, or one byte larger than `100000000` otherwise.

```bash
temp_payload="$(mktemp /tmp/wild-catalog-oversized.XXXXXX)"
dd if=/dev/zero of="$temp_payload" bs=1m count=96 2>/dev/null
curl -i -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/octet-stream' \
  -H 'x-filename: oversized.bin' \
  --data-binary "@$temp_payload"
rm -f "$temp_payload"
```

## Direct HEIC Upload

HEIC and HEIF are detected, but the service currently rejects them as unsupported image formats.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: image/heic' \
  -H 'x-filename: 20260525-IMG_7906.heic' \
  --data-binary '@sample-images/20260525-IMG_7906.heic'
```

## Notes

* Do not combine `-F` with `Content-Type: image/jpeg` on the same request. `-F` sends `multipart/form-data`, so forcing a single-part image content type creates a malformed request shape.
* For direct uploads, set `x-filename` so the server can detect RAW formats from the filename when needed.
* For multipart uploads, the filename attached to the `image` part is usually enough.
* Multipart requests currently use the same image sample as the direct JPEG upload scenarios. The script keeps the multipart request shapes separate so each transport is tested explicitly.
* The script uses `curl -sS` so the response is easier to scan; it still prints the API response body.

## Related Tests

These commands mirror the scenarios covered by:

* `tests/integration/api/test_api_layer.py`
* `tests/integration/conversion/test_standard.py`
* `tests/integration/conversion/test_raw.py`

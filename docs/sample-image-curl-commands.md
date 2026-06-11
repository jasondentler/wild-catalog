# Sample Image Curl Commands

This document collects `curl` commands for exercising `POST /identify` with the sample images in `sample-images/`.

## Files Used

* `sample-images/20260402-IMG_7906.jpg`
* `sample-images/20260419-DA8A0090.jpg`
* `sample-images/20260419-DA8A5083.jpg`
* `sample-images/20260419-DA8A5151.jpg`
* `sample-images/20260419-DA8A5506.jpg`
* `sample-images/20260419-DA8A7718.jpg`
* `sample-images/20260525-IMG_7906.heic`
* `sample-images/20260525-IMG_7906.CR3`

Assume the API is running at `http://127.0.0.1:8000`.

## Direct JPEG Upload

Use this for the standard raw upload path.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: image/jpeg' \
  -H 'x-filename: 20260402-IMG_7906.jpg' \
  --data-binary '@sample-images/20260402-IMG_7906.jpg'
```

## Multipart JPEG Upload

Use this when sending an image as `multipart/form-data`.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -F 'image=@sample-images/20260402-IMG_7906.jpg;type=image/jpeg'
```

## Multipart JPEG Upload With Payload

Use this when you want to supply request metadata alongside the upload.

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

Use this for RAW files that the service recognizes by filename, such as CR3.

```bash
curl -X POST 'http://127.0.0.1:8000/identify' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/octet-stream' \
  -H 'x-filename: 20260525-IMG_7906.CR3' \
  --data-binary '@sample-images/20260525-IMG_7906.CR3'
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

## Related Tests

These commands mirror the scenarios covered by:

* `tests/integration/api/test_api_layer.py`
* `tests/integration/conversion/test_sample_images.py`

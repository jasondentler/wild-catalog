#!/usr/bin/env bash

set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
SAMPLE_DIR="${SAMPLE_DIR:-sample-images}"

JPEG_IMAGE_1="${SAMPLE_DIR}/20260402-IMG_7906.jpg"
JPEG_IMAGE_2="${SAMPLE_DIR}/20260419-DA8A0090.jpg"
JPEG_IMAGE_3="${SAMPLE_DIR}/20260419-DA8A5083.jpg"
JPEG_IMAGE_4="${SAMPLE_DIR}/20260419-DA8A5151.jpg"
JPEG_IMAGE_5="${SAMPLE_DIR}/20260419-DA8A5506.jpg"
JPEG_IMAGE_6="${SAMPLE_DIR}/20260419-DA8A7718.jpg"
PNG_IMAGE="${SAMPLE_DIR}/20260402-IMG_7906.png"
WEBP_IMAGE="${SAMPLE_DIR}/20260402-IMG_7906.webp"
HEIC_IMAGE="${SAMPLE_DIR}/20260525-IMG_7906.heic"
CR3_IMAGE="${SAMPLE_DIR}/20260525-IMG_7906.CR3"
DNG_IMAGE="${SAMPLE_DIR}/20260525-IMG_7906.dng"
DNG_IMAGE_2="${SAMPLE_DIR}/20260525-IMG_7906_1.dng"
MAX_UPLOAD_BYTES="${WILD_CATALOG_MAX_UPLOAD_BYTES:-100000000}"
HUGE_PAYLOAD_SIZE_BYTES="${HUGE_PAYLOAD_SIZE_BYTES:-$((MAX_UPLOAD_BYTES + 1))}"

usage() {
  cat <<'EOF'
Usage:
  scripts/sample-image-curls.sh [scenario|all]

Scenarios:
  direct-jpeg
  direct-jpeg-2
  direct-jpeg-3
  direct-jpeg-4
  direct-jpeg-5
  direct-jpeg-6
  direct-png
  direct-webp
  multipart-jpeg
  multipart-jpeg-payload
  multipart-jpeg-no-payload
  direct-raw
  direct-dng
  direct-dng-2
  direct-heic
  direct-oversized
  multipart-large-payload
  all

Environment:
  API_URL     Base API URL. Default: http://127.0.0.1:8000
  SAMPLE_DIR  Directory containing sample images. Default: sample-images
EOF
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing file: $path" >&2
    exit 1
  fi
}

announce() {
  echo
  echo "== $1 =="
}

direct_jpeg() {
  require_file "$JPEG_IMAGE_1"
  announce "Direct JPEG upload"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/jpeg' \
    -H 'x-filename: 20260402-IMG_7906.jpg' \
    --data-binary "@${JPEG_IMAGE_1}"
}

direct_jpeg_2() {
  require_file "$JPEG_IMAGE_2"
  announce "Direct JPEG upload 2"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/jpeg' \
    -H 'x-filename: 20260419-DA8A0090.jpg' \
    --data-binary "@${JPEG_IMAGE_2}"
}

direct_jpeg_3() {
  require_file "$JPEG_IMAGE_3"
  announce "Direct JPEG upload 3"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/jpeg' \
    -H 'x-filename: 20260419-DA8A5083.jpg' \
    --data-binary "@${JPEG_IMAGE_3}"
}

direct_jpeg_4() {
  require_file "$JPEG_IMAGE_4"
  announce "Direct JPEG upload 4"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/jpeg' \
    -H 'x-filename: 20260419-DA8A5151.jpg' \
    --data-binary "@${JPEG_IMAGE_4}"
}

direct_jpeg_5() {
  require_file "$JPEG_IMAGE_5"
  announce "Direct JPEG upload 5"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/jpeg' \
    -H 'x-filename: 20260419-DA8A5506.jpg' \
    --data-binary "@${JPEG_IMAGE_5}"
}

direct_jpeg_6() {
  require_file "$JPEG_IMAGE_6"
  announce "Direct JPEG upload 6"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/jpeg' \
    -H 'x-filename: 20260419-DA8A7718.jpg' \
    --data-binary "@${JPEG_IMAGE_6}"
}

direct_png() {
  require_file "$PNG_IMAGE"
  announce "Direct PNG upload"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/png' \
    -H 'x-filename: 20260402-IMG_7906.png' \
    --data-binary "@${PNG_IMAGE}"
}

direct_webp() {
  require_file "$WEBP_IMAGE"
  announce "Direct WebP upload"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/webp' \
    -H 'x-filename: 20260402-IMG_7906.webp' \
    --data-binary "@${WEBP_IMAGE}"
}

multipart_jpeg() {
  require_file "$JPEG_IMAGE_1"
  announce "Multipart JPEG upload"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -F "image=@${JPEG_IMAGE_1};type=image/jpeg"
}

multipart_jpeg_payload() {
  require_file "$JPEG_IMAGE_1"
  announce "Multipart JPEG upload with payload"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: multipart/mixed' \
    -F "image=@${JPEG_IMAGE_1};type=image/jpeg" \
    -F 'payload={"original_filename":"override-name.jpg","return_detected_images":true,"common_name_language":"es-MX"};type=application/json'
}

multipart_jpeg_no_payload() {
  require_file "$JPEG_IMAGE_1"
  announce "Multipart JPEG upload without payload"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -F "image=@${JPEG_IMAGE_1};type=image/jpeg"
}

direct_raw() {
  require_file "$CR3_IMAGE"
  announce "Direct RAW upload (CR3)"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: application/octet-stream' \
    -H 'x-filename: 20260525-IMG_7906.CR3' \
    --data-binary "@${CR3_IMAGE}"
}

direct_dng() {
  require_file "$DNG_IMAGE"
  announce "Direct RAW upload (DNG)"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: application/octet-stream' \
    -H 'x-filename: 20260525-IMG_7906.dng' \
    --data-binary "@${DNG_IMAGE}"
}

direct_dng_2() {
  require_file "$DNG_IMAGE_2"
  announce "Direct RAW upload (DNG 2)"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: application/octet-stream' \
    -H 'x-filename: 20260525-IMG_7906_1.dng' \
    --data-binary "@${DNG_IMAGE_2}"
}

direct_heic() {
  require_file "$HEIC_IMAGE"
  announce "Direct HEIC upload"
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/heic' \
    -H 'x-filename: 20260525-IMG_7906.heic' \
    --data-binary "@${HEIC_IMAGE}"
}

direct_oversized() {
  local temp_payload
  local curl_status=0
  temp_payload="$(mktemp "${TMPDIR:-/tmp}/wild-catalog-oversized.XXXXXX")"

  dd if=/dev/zero of="$temp_payload" bs=1m count="$(( (HUGE_PAYLOAD_SIZE_BYTES + 1048575) / 1048576 ))" 2>/dev/null

  announce "Oversized payload upload to test the content-length limiter"
  set +e
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: application/octet-stream' \
    -H 'x-filename: oversized.bin' \
    --data-binary "@${temp_payload}"
  curl_status=$?
  set -e

  rm -f "$temp_payload"

  return "$curl_status"
}

multipart_large_payload() {
  require_file "$JPEG_IMAGE_1"

  local temp_payload
  local curl_status=0
  temp_payload="$(mktemp "${TMPDIR:-/tmp}/wild-catalog-large-payload.XXXXXX")"

  dd if=/dev/zero of="$temp_payload" bs=1m count="$(( (HUGE_PAYLOAD_SIZE_BYTES + 1048575) / 1048576 ))" 2>/dev/null

  announce "Multipart upload with a large payload to test the content-length limiter"
  set +e
  curl -sS -X POST "${API_URL}/identify" \
    -H 'accept: multipart/mixed' \
    -F "image=@${JPEG_IMAGE_1};type=image/jpeg" \
    -F "payload=@${temp_payload};type=application/json"
  curl_status=$?
  set -e

  rm -f "$temp_payload"

  return "$curl_status"
}

all() {
  direct_jpeg
  direct_jpeg_2
  direct_jpeg_3
  direct_jpeg_4
  direct_jpeg_5
  direct_jpeg_6
  direct_png
  direct_webp
  multipart_jpeg
  multipart_jpeg_payload
  multipart_jpeg_no_payload
  direct_raw
  direct_dng
  direct_dng_2
  direct_heic
  direct_oversized
  multipart_large_payload
}

main() {
  local scenario="${1:-all}"

  case "$scenario" in
    direct-jpeg)
      direct_jpeg
      ;;
    direct-jpeg-2)
      direct_jpeg_2
      ;;
    direct-jpeg-3)
      direct_jpeg_3
      ;;
    direct-jpeg-4)
      direct_jpeg_4
      ;;
    direct-jpeg-5)
      direct_jpeg_5
      ;;
    direct-jpeg-6)
      direct_jpeg_6
      ;;
    direct-png)
      direct_png
      ;;
    direct-webp)
      direct_webp
      ;;
    multipart-jpeg)
      multipart_jpeg
      ;;
    multipart-jpeg-payload)
      multipart_jpeg_payload
      ;;
    multipart-jpeg-no-payload)
      multipart_jpeg_no_payload
      ;;
    direct-raw)
      direct_raw
      ;;
    direct-dng)
      direct_dng
      ;;
    direct-dng-2)
      direct_dng_2
      ;;
    direct-heic)
      direct_heic
      ;;
    direct-oversized)
      direct_oversized
      ;;
    multipart-large-payload)
      multipart_large_payload
      ;;
    all)
      all
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"

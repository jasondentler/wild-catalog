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
HEIC_IMAGE="${SAMPLE_DIR}/20260525-IMG_7906.heic"
CR3_IMAGE="${SAMPLE_DIR}/20260525-IMG_7906.CR3"

usage() {
  cat <<'EOF'
Usage:
  scripts/sample-image-curls.sh [scenario|all]

Scenarios:
  direct-jpeg
  multipart-jpeg
  multipart-jpeg-payload
  multipart-jpeg-no-payload
  direct-raw
  direct-heic
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

direct_jpeg() {
  require_file "$JPEG_IMAGE_1"
  curl -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/jpeg' \
    -H 'x-filename: 20260402-IMG_7906.jpg' \
    --data-binary "@${JPEG_IMAGE_1}"
}

multipart_jpeg() {
  require_file "$JPEG_IMAGE_1"
  curl -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -F "image=@${JPEG_IMAGE_1};type=image/jpeg"
}

multipart_jpeg_payload() {
  require_file "$JPEG_IMAGE_1"
  curl -X POST "${API_URL}/identify" \
    -H 'accept: multipart/mixed' \
    -F "image=@${JPEG_IMAGE_1};type=image/jpeg" \
    -F 'payload={"original_filename":"override-name.jpg","return_detected_images":true,"common_name_language":"es-MX"};type=application/json'
}

multipart_jpeg_no_payload() {
  require_file "$JPEG_IMAGE_1"
  curl -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -F "image=@${JPEG_IMAGE_1};type=image/jpeg"
}

direct_raw() {
  require_file "$CR3_IMAGE"
  curl -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: application/octet-stream' \
    -H 'x-filename: 20260525-IMG_7906.CR3' \
    --data-binary "@${CR3_IMAGE}"
}

direct_heic() {
  require_file "$HEIC_IMAGE"
  curl -X POST "${API_URL}/identify" \
    -H 'accept: application/json' \
    -H 'Content-Type: image/heic' \
    -H 'x-filename: 20260525-IMG_7906.heic' \
    --data-binary "@${HEIC_IMAGE}"
}

all() {
  direct_jpeg
  multipart_jpeg
  multipart_jpeg_payload
  multipart_jpeg_no_payload
  direct_raw
  direct_heic
}

main() {
  local scenario="${1:-all}"

  case "$scenario" in
    direct-jpeg)
      direct_jpeg
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
    direct-heic)
      direct_heic
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

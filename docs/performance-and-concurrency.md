# Performance and Concurrency

[Architecture](./architecture.md)
[Deployments](./deployments.md)
[Implementation Plan](./implementation-plan.md)

Wild Catalog targets warm-path `/identify` responses under 500ms where practical. This target assumes models and local lookup data are already loaded and does not include first-time downloads, full range-map builds, DarwinCore Archive parsing, very large RAW decoding, or platform conversion failures.

## Bounded concurrency

Real detector and classifier inference can consume significant memory and accelerator resources. Add a bounded concurrency guard around `/identify`.

Recommended controls:

```text
WILD_CATALOG_MAX_CONCURRENT_IDENTIFY_REQUESTS=1
```

The guard should protect:

```text
MPS
CUDA VRAM
CPU RAM
model objects
SQLite connections
```

When saturated, the API should either queue briefly or return a controlled `503 Service Unavailable` depending on the configured policy.

## Timing instrumentation

Record per-stage timing for:

```text
request parsing
image conversion
detection
deduplication
cropping
classification
prior lookup
logit conditioning
taxonomy enrichment
serialization
total request time
```

Timing should be logged with a request ID. Do not log raw image data, crop bytes, model weights, or large payloads.

## Memory rules

Use these rules throughout the pipeline:

1. Enforce upload size before decoding.
2. Enforce max image pixels after decoding/conversion.
3. Convert to RGB once.
4. Deduplicate and cap detections before cropping.
5. Keep crops only as long as needed.
6. Only retain crop images in the final result when `return_detected_images=true`.
7. Avoid accumulating full model outputs when top-k results are enough.
8. Use local SQLite stores for taxonomy/range lookup instead of large request-time parses.

## Startup warmup and latency

`WILD_CATALOG_PRELOAD_MODELS=true` is the default. Startup should load the detector, classifier, taxonomy store, and range prior store before `/identify` is ready. Clients should poll `GET /status` and only send `/identify` traffic once `ready=true`.

## Result-quality policy

Final confidence filtering should run after logit conditioning and before API serialization. It should be configurable and should not live inside detector or classifier plugins.

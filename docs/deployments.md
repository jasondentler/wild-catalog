# Deploying Wild Catalog

[Architecture](./architecture.md)
[API Gateway](./api-gateway.md)
[Implementation Plan](./implementation-plan.md)

This guide describes how to run Wild Catalog in production-like environments and how to operate its startup readiness model.

## Deployment goals

Wild Catalog should serve warm `/identify` requests with models and local lookup data already loaded. The API should not perform first-time model downloads, taxonomy downloads, range-map compilation, or DarwinCore Archive parsing during request handling.

The normal deployment flow is:

1. Build the application image or runtime environment.
2. Run pre-operational tasks to prepare durable local assets.
3. Start the API server.
4. Poll `GET /status` until `ready=true`.
5. Route client `POST /identify` traffic to the instance.

## Required local assets

Production deployments should prepare these assets before receiving traffic:

* Detector model weights.
* Species classifier model weights.
* Local taxonomy archive or compiled taxonomy store derived from `taxonomy.dwca.zip`.
* Local SQLite species range prior store.

Use the configured pre-operational commands to prepare them:

```bash
make preop
```

Individual commands may include:

```bash
make preop-range-maps
make preop-classifier-model
make preop-detector-model
```

Do not run these setup tasks from inside `POST /identify`. Do not shell out to `make preop` from FastAPI startup. Startup should validate and warm prepared assets, not rebuild expensive datasets on every process start.

## Startup readiness model

The default startup mode is eager preload:

```text
WILD_CATALOG_PRELOAD_MODELS=true
```

At startup, the API should:

1. Build settings.
2. Build exactly one identify pipeline.
3. Store the pipeline in `app.state`.
4. Warm the detector model.
5. Warm the classifier model.
6. Load the taxonomy store.
7. Open and lightly validate the range prior store.
8. Optionally run tiny synthetic inference.
9. Mark the service ready only after required tasks complete.

The same warmed pipeline must be used by `/identify`. Do not warm one pipeline and serve requests with another.

## Health vs status

Use `GET /health` for lightweight process checks:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

`GET /health` must not load models, parse taxonomy data, open range-map stores, or run inference.

Use `GET /status` for readiness and startup progress:

```http
GET /status
```

It reports:

* overall startup state;
* whether `/identify` is ready;
* whether model preloading is enabled;
* elapsed startup time;
* estimated seconds remaining, when available;
* per-task status and progress;
* failure codes and messages.

Clients and load balancers that need readiness should poll `GET /status` and wait for:

```json
{
  "ready": true
}
```

## `/identify` while warming

If `POST /identify` is called before startup warming completes, the API returns:

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
Retry-After: 10
```

```json
{
  "error": {
    "code": "service_not_ready",
    "message": "Wild Catalog is still warming required models and local data. Call GET /status for startup progress and estimated readiness.",
    "request_id": "..."
  }
}
```

`Retry-After` should be included only when the backend can produce a reasonable estimate.

If startup failed, `/identify` returns `503` with `startup_failed` and instructs clients to call `GET /status` for details.

## Development opt-out

For local development only, you can disable eager preload:

```bash
WILD_CATALOG_PRELOAD_MODELS=false make serve
```

This lets the server become ready quickly and may defer expensive model loading. Do not use this mode for production benchmarking or latency-sensitive deployments.

## Important environment variables

```text
WILD_CATALOG_ENV=production
WILD_CATALOG_PRELOAD_MODELS=true
WILD_CATALOG_STARTUP_SYNTHETIC_INFERENCE_ENABLED=true
WILD_CATALOG_MAX_CONCURRENT_IDENTIFY_REQUESTS=1
WILD_CATALOG_DETECTOR_BACKEND=grounding-dino
WILD_CATALOG_CLASSIFIER_BACKEND=birder-inat21
WILD_CATALOG_RANGE_MAP_STORE_PATH=data/range-maps/ranges.sqlite3
WILD_CATALOG_TAXONOMY_DWCA_PATH=data/taxonomy/taxonomy.dwca.zip
WILD_CATALOG_TAXONOMY_STORE_PATH=data/taxonomy
```

Keep concurrency conservative until real memory and latency measurements prove it is safe to raise.

## Storage and cleanup

Generated local state should live under `data/` where practical:

```text
data/models/
data/range-maps/
data/taxonomy/
data/cache/
```

`make clean` may remove `data/` and `.venv`. Do not store committed fixtures such as `sample-images/` under `data/`.

## Operational client behavior

Recommended client startup behavior:

1. Poll `GET /status`.
2. Wait until `ready=true`.
3. Send `POST /identify`.
4. If `POST /identify` returns `503`, inspect `GET /status` and retry later.

Recommended content negotiation behavior for clients requesting detected crop images:

```http
Accept: multipart/mixed
```

If `return_detected_images=true` and the client only accepts `application/json`, Wild Catalog returns `406 Not Acceptable`.

## Deployment checklist

Before routing production traffic to an instance:

```text
[ ] make preop has prepared required durable assets.
[ ] Detector model is available.
[ ] Classifier model is available.
[ ] Taxonomy data is available locally.
[ ] Range prior SQLite store is available locally.
[ ] WILD_CATALOG_PRELOAD_MODELS=true.
[ ] GET /health returns 200.
[ ] GET /status returns ready=true.
[ ] POST /identify has been smoke-tested with a small JPEG.
[ ] Logs include request IDs and startup timing.
[ ] Memory usage has been checked under expected concurrency.
```

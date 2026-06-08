# Asset Management

[Architecture](./architecture.md)
[Deployments](./deployments.md)
[Implementation Plan](./implementation-plan.md)

Wild Catalog uses durable local assets for real model inference and offline taxonomy/range lookup. These assets are prepared before request handling and warmed or validated at startup.

## Asset categories

```text
data/models/       Detector and classifier weights or model caches
data/taxonomy/     taxonomy.dwca.zip and/or compiled taxonomy store
data/range-maps/   compiled SQLite range-prior store and downloaded GeoPackages
data/cache/        optional runtime caches
```

Exact paths are configurable. Public API responses and `/status` must not expose local filesystem paths.

## Preop responsibilities

`make preop` and specific preop commands prepare durable assets:

```bash
make preop
make preop-range-maps
make preop-classifier-model
make preop-detector-model
```

Preop may download models, download `taxonomy.dwca.zip`, download range-map archives, and build compiled SQLite stores. Preop should be safe to rerun and should reuse valid existing assets.

## Startup responsibilities

FastAPI startup should validate and warm prepared assets:

```text
load detector model
load classifier model
load/open taxonomy store
open/validate range prior store
optionally run tiny synthetic inference
```

Startup should not rebuild the full range-map store or parse the full DarwinCore Archive unless a future configuration explicitly opts into that behavior.

## Request-time responsibilities

`POST /identify` should only use warmed assets. It must not:

```text
download model weights
download taxonomy.dwca.zip
parse the full taxonomy archive
build the range-map SQLite store
call live iNaturalist APIs
```

If assets are missing or invalid, startup status should fail, and `/identify` should return `503 Service Unavailable` with a message directing clients to `GET /status`.

## Version metadata

Compiled stores should include source/version metadata. `/status` may report non-sensitive metadata such as:

```text
detector backend and model id
classifier backend and model id
classifier class_index_id
taxonomy source/version
range-map source/version
range geometry format
built_at timestamps
```

Do not expose local paths, credentials, raw command output, or stack traces.

## Cleaning generated assets

`make clean` may remove generated `data/` state in development. After cleaning, run `make preop` again before real-model integration tests or production-like startup.

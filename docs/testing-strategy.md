# Testing Strategy

[Architecture](./architecture.md)
[Contributing](./contributing.md)
[Implementation Plan](./implementation-plan.md)

Wild Catalog tests are split between fast unit tests and slower integration tests.

## Required test locations

All tests must live under one of these folders:

```text
tests/unit/
tests/integration/
```

Do not create tests directly under `tests/`.

## Unit tests

Unit tests should use fakes, stubs, and tiny fixtures. They should not download models, parse full taxonomy archives, build full range-map stores, or call live APIs.

Use unit tests for:

```text
API request/response behavior
content negotiation
error mapping
startup status state
readiness guard
box conversion
crop clamping
deduplication policy
logit conditioning math
taxonomy fallback behavior
import-boundary rules
```

## Integration tests

Integration tests may use real sample images and prepared local assets. They should live under `tests/integration/` and run through the existing `make test` behavior.

Do not add new Makefile commands for individual tests.

Integration tests should cover:

```text
real Grounding DINO detector on sample images
real Birder classifier on sample images
classifier/prior/conditioning/taxonomy regression fixtures
full internal IdentifyPipeline smoke tests
optional API smoke tests with fake or prepared assets
```

## Sample images

Prefer existing files under `sample-images/` for real-model integration tests. The curated cormorant regression image is:

```text
sample-images/20260402-IMG_7906.jpg
```

That test should assert Neotropic Cormorant / `Nannopterum brasilianum` for the classifier/prior/conditioning/taxonomy chain.

## Makefile policy

Use existing commands:

```bash
make test-fast
make lint
make test
make pr
```

The Makefile test behavior is locked. Do not add new testing commands without human approval.

## External services

Tests must not call live iNaturalist APIs during `/identify` or normal test execution. Tests should use local prepared assets, fixtures, or fakes.

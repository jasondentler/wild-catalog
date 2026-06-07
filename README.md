# Wild Catalog

Wild Catalog is an open-source tool that looks at nature photos and automatically figures out what animals, plants, and fungi are in them. It identifies the species, traces their scientific family tree, and looks up their common names.

Wild Catalog is built to power the [Crush-Catalog Lightroom plugin](https://github.com/jasondentler/crush-catalog), but Wild Catalog is intentionally frontend-agnostic. Lightroom, desktop tools, web clients, CLI tools, or other cataloging systems can call the API as long as they follow the documented request contract.

## Goals

* Identify animals, plants, fungi, lichens, and other nature subjects in catalog photos.
* Keep detector and classifier models pluggable so the project can adopt better models over time.
* Avoid license-problematic runtime dependencies.
* Keep the API stable even when model implementations change.
* Keep memory use low by converting once, deduplicating before cropping, batching model inference, and only returning crop images when requested.
* Keep warm-path API responses under 500ms where practical.

## Current model strategy

Wild Catalog uses model plugin interfaces rather than hard-coding a specific detector or classifier into the pipeline.

Default planned production plugins:

* **Detector**: Grounding DINO-compatible open-vocabulary detector using an organism-focused prompt.
* **Classifier**: Birder/iNaturalist-compatible species classifier returning raw logits for geographic conditioning.

Default test plugins:

* `StubObjectDetector`
* `StubSpeciesClassifier`

Stub plugins keep unit and API contract tests fast and deterministic without model downloads.

## HEIC/HEIF support

Wild Catalog does not use `pillow-heif` or native Python HEIC decoding dependencies. Instead, HEIC/HEIF files may be handled by optional platform image conversion adapters before entering the normal Pillow JPEG path.

Supported conversion approaches may include:

* macOS: `sips`
* Linux: ImageMagick `magick` or `heif-convert`
* Windows: ImageMagick `magick` or a Windows Imaging Component / PowerShell adapter

Clients may also convert HEIC/HEIF to JPEG before upload, especially in Lightroom workflows.

## Documentation

* [API Gateway](./docs/api-gateway.md)
* [System Architecture](./docs/architecture.md)
* [Image Conversion Service](./docs/image-conversion-service.md)
* [Detection Service](./docs/detection-service.md)
* [Duplicate Detection Service](./docs/deduplicate-detection-service.md)
* [Image Cropping Service](./docs/image-cropping-service.md)
* [Species Classifier Service](./docs/species-classifier-service.md)
* [Species Range Prior Service](./docs/species-range-prior-service.md)
* [Logit Conditioning Layer](./docs/logit-conditioning-layer.md)
* [Implementation Plan](./docs/implementation-plan.md)
* [Contributing](./docs/contributing.md)

## License

Copyright 2026 Jason Dentler

Source code in this repository is licensed under the [Apache License, Version 2.0](./LICENSE.txt). Sample images and other photographic assets are not licensed under Apache 2.0. See [NOTICE.txt](./NOTICE.txt) for details.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at:

```text
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

*This software is not affiliated with or endorsed by Adobe, Cornell University, eBird, or iNaturalist.*

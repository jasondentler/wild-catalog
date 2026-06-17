# Wild Catalog

Wild Catalog is an open-source tool that looks at nature photos and automatically figures out what animals are in them. It identifies the species, traces their scientific family tree, and looks up their common names. Built to power the [Crush-Catalog Lightroom plugin](https://github.com/jasondentler/crush-catalog), it lets you easily search, sort, and catalog wildlife pictures.

## Table of Contents

* [Contributing](./CONTRIBUTING.md)
* [Third-Party Notices](./third-party-notices.md)

## Development Setup

Use the repository [`makefile`](./makefile) to create the local Python 3.13 environment and install dependencies:

```bash
make
```

The install flow bootstraps [`uv`](https://docs.astral.sh/uv/) inside `.venv` and uses it to resolve the project dependencies, including the PyTorch Wildlife stack. See [Contributing](./CONTRIBUTING.md) for platform setup details and lockfile workflow.

## License

Copyright 2026 Jason Dentler

Source code in this repository is licensed under the [Apache License, Version 2.0](./LICENSE.txt). Sample images and other photographic assets are not licensed under Apache 2.0. See [NOTICE.txt](./NOTICE.txt) for details. Third-party open source package notices are listed in [third-party-notices.md](./third-party-notices.md).

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at:

```text
http://www.apache.org/licenses/LICENSE-2.0
```

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

*This software is not affiliated with or endorsed by Adobe, Cornell University, eBird, or iNaturalist.*

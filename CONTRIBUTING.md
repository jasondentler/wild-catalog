# Contributing to Wild Catalog

Thank you for your interest in contributing to my project! I welcome all contributions, whether it is reporting a bug, improving documentation, or submitting new features.

To ensure a smooth process for everyone involved, please review the following guidelines.

## 🚀 Getting Started

This assumes you have [`git`](https://git-scm.com/) installed and are comfortable working at the terminal.

### 1. Fork and Clone the Project
Go to the [Wild Catalog GitHub Repository](https://github.com/jasondentler/wild-catalog) and click the **Fork** button in the top-right corner. This creates a personal copy under your account. 

Clone your fork locally (replace `YOUR_USERNAME` with your actual GitHub username) and enter the directory:

```bash
git clone https://github.com/YOUR_USERNAME/wild-catalog.git
cd wild-catalog
```

> 💡 **Prefer the [GitHub CLI](https://cli.github.com/)?** 
> Skip the web UI entirely and fork/clone in a single command:
> ```bash
> gh repo fork jasondentler/wild-catalog --clone
> cd wild-catalog
> ```

### 2. Track the Main Project (Upstream)
Keep your local fork in sync with future updates from the main repository by adding a remote link to the original project:

```bash
git remote add upstream https://github.com/jasondentler/wild-catalog.git
```

---

## 🛠️ Environment Setup

### 🍏 Option A: macOS Setup

#### Step 1: Install Xcode Command Line Tools
Install Apple's [Xcode Command Line Tools](https://developer.apple.com/xcode/resources/) (including [`make`](https://www.gnu.org/software/make/) and [`git`](https://git-scm.com/) tools):

```bash
xcode-select --install
```

> 💡 **What to expect:** A system popup window will appear asking for confirmation. Click **Install**, accept the terms, and allow the download to finish. If you see an error stating they are already installed, safely skip this step.

Verify the [`make`](https://www.gnu.org/software/make/) installation succeeded:
```bash
make --version
```

#### Step 2: Install Python 3.13 via Homebrew
Ensure you have **[Homebrew](https://brew.sh/)** installed. If you do not have it yet, set it up by running:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Once [Homebrew](https://brew.sh/) is ready, install [Python 3.13](https://www.python.org/downloads/release/python-3130/):
```bash
brew install python@3.13
```

#### Step 3: Run the Makefile
Build your environment, install dependencies, lint, and run the test suite with [`make`](https://www.gnu.org/software/make/):
```bash
make
```

The install step creates `.venv`, installs a local copy of [`uv`](https://docs.astral.sh/uv/), and then uses that `.venv` copy of `uv` to install the project with development dependencies.

---

### 🪟 Option B: Windows Setup

#### Step 1: Install Chocolatey Package Manager
Open [PowerShell](https://learn.microsoft.com/powershell/) **as Administrator** and install [Chocolatey](https://chocolatey.org/install) (if you do not have it yet):
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### Step 2: Install [Python 3.13](https://www.python.org/downloads/release/python-3130/) and [GNU Make](https://www.gnu.org/software/make/)
Run the following [Chocolatey](https://chocolatey.org/) package install commands:
```powershell
choco install python3 --version=3.13.0 -y
choco install make -y
```

> ⚠️ **Important:** Close and completely reopen your terminal window after this step so your system recognizes the newly installed tools.

#### Step 3: Run the Makefile
Build your environment, install dependencies, lint, and run the test suite with [`make`](https://www.gnu.org/software/make/):
```powershell
make
```

The install step creates `.venv`, installs a local copy of [`uv`](https://docs.astral.sh/uv/), and then uses that `.venv` copy of `uv` to install the project with development dependencies.

---

### 🐧 Option C: Linux Setup (Ubuntu/Debian)

#### Step 1: Install Build Essentials and Prerequisites
Ensure your system package manager is up to date and install the core [build-essential](https://packages.debian.org/bookworm/build-essential) infrastructure utilities (which include [`make`](https://www.gnu.org/software/make/)):

```bash
sudo apt update
sudo apt install build-essential software-properties-common -y
```

#### Step 2: Install Python 3.13
Add the [deadsnakes PPA archive](https://launchpad.net/%7Edeadsnakes/+archive/ubuntu/ppa) to your system to access the [Python 3.13](https://www.python.org/downloads/release/python-3130/) runtime binaries and its [`venv`](https://docs.python.org/3/library/venv.html) virtual environment modules:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.13 python3.13-venv -y
```

#### Step 3: Run the Makefile
Build your isolated environment, download app dependencies, lint, and run the testing loops with [`make`](https://www.gnu.org/software/make/):
```bash
make
```

The install step creates `.venv`, installs a local copy of [`uv`](https://docs.astral.sh/uv/), and then uses that `.venv` copy of `uv` to install the project with development dependencies.

---

## Dependency Management

Wild Catalog uses [`uv`](https://docs.astral.sh/uv/) for project dependency resolution after the virtual environment has been created.

The default setup path is:

```bash
make install
```

That target:

* upgrades `pip`
* constrains `setuptools<82` for compatibility with the installed PyTorch stack
* installs `uv` into `.venv`
* installs the project with development dependencies using `.venv/bin/uv pip install -e ".[dev]"`

The PyTorch-Wildlife detector stack is a required dependency. The project pins `PytorchWildlife` in `pyproject.toml`, and uses `[tool.uv].override-dependencies` to prevent `uv` from resolving GPL/AGPL YOLO packages that are not part of the intended runtime dependency set.

The runtime detector uses PyTorch-Wildlife's Apache RT-DETR MegaDetector v6 backend (`MegaDetectorV6Apache`) by default. Some PyTorch-Wildlife package imports still reference optional audio, TensorBoard, YOLO, or Ultralytics modules even when the Apache RT-DETR backend is the only detector being used. Wild Catalog provides narrow import compatibility shims for those unused optional paths so the runtime dependency set stays aligned with the intended detector backend.

### Lockfile Workflow

Generate or update the lockfile from the repository root:

```bash
.venv/bin/uv lock
```

On Windows, use `.venv/Scripts/uv` instead of `.venv/bin/uv`.

Do not pass `--extra dev` to `uv lock`; this project's installed `uv` version selects extras during sync or install, not during lockfile generation.

To sync a development environment from the lockfile:

```bash
.venv/bin/uv sync --extra dev
```

Commit `uv.lock` alongside any dependency changes in `pyproject.toml`.

After changing dependencies, verify the environment:

```bash
.venv/bin/python -m pip check
make license-check
```

If `licensecheck` reports dependencies that `uv` is intentionally overriding, verify the installed environment with `pip check` and review the resolver configuration in `pyproject.toml` before changing license policy.

When the installed dependency set changes, regenerate [third-party-notices.md](./third-party-notices.md):

```bash
make third-party-notices
```

The `third-party-notices` target runs `scripts/update_third_party_notices.py`, which calls `licensecheck` with JSON output and reads dependencies from `pyproject.toml` explicitly. Commit notice updates alongside the dependency changes that caused them.

## 💡 Daily Development Shortcuts

Once your environment is built via the initial [`make`](https://www.gnu.org/software/make/) invocation, use these shortcuts for quick local development loops:

*   **`make serve`** — Starts the local [Uvicorn](https://www.uvicorn.org/) API server with live code auto-reload enabled.
*   **`make test-fast`** — Runs lightweight unit tests immediately while skipping heavyweight integration checks.
*   **`make test`** — Runs the full test suite, including end-to-end integration checks.
*   **`make lint`** — Runs code linting checks using [Ruff](https://ruff.rs/).
*   **`make lint-fix`** — Automatically fixes safe code style errors and organizes imports.
*   **`make third-party-notices`** — Regenerates [third-party-notices.md](./third-party-notices.md) from the installed dependency metadata.
*   **`make clean`** — Wipes generated local state, including `.venv` and `data/`, if you need to perform a fresh reinstall.

## Docker

Build and start the API with Docker Compose:

```bash
docker compose up --build
```

The API is available at <http://localhost:8000>, with its health endpoint at
<http://localhost:8000/health>. Compose stores downloaded models, taxonomy, and range data in
the `wild-catalog-data` volume so they survive container replacement. The initial startup runs
the application's pre-operation imports and can take a long time and require several gigabytes
of disk space; subsequent starts reuse the volume.

Compose downloads the MegaDetector weights from Zenodo. Set
`WILD_CATALOG_MDV6_MODEL_URL` to use a mirror or local model server instead.

To stop the service without deleting its downloaded data:

```bash
docker compose down
```

The equivalent Make targets are `make docker-build`, `make docker-up`, and `make docker-down`.


## Pre-operational data and model setup

Wild Catalog separates durable setup work from request-time `/identify` behavior. `POST /identify` should not download models, download taxonomy archives, compile range maps, or parse large raw data archives.

Detector assets currently use these project-local paths:

```text
data/models/MDV6-apa-rtdetr-e.pth
data/models/torch-hub/
```

Set `TORCH_HOME` if you need Torch Hub to use a different cache location.

Use the pre-operational commands before running real-model workflows:

```bash
make preop
```

This runs the configured pre-operational tasks as a group. Individual tasks may include:

```bash
make preop-classifier-model
make preop-detector-model
make preop-range-maps
make preop-taxonomy-dwca
```

The detector preop flow is the intended durable setup path for MegaDetector weights and the RT-DETR backbone cache. Until that command is re-added, detector integration tests may still download those assets on demand.

Do not add new make commands for testing. Use the existing test commands:

```bash
make test-fast
make test
make pr
```

## Running the API locally

Run the API with:

```bash
make serve
```

The current API exposes `GET /health`, `GET /openapi.json`, and `POST /identify`.

`GET /health` is a lightweight heartbeat. It does not verify model availability or perform detector warmup.

## 🛠️ Development Workflow

### Code Style & Linting
I use [Ruff](https://ruff.rs) to enforce code formatting and catch potential issues. Before committing with [`git`](https://git-scm.com/), run the linter shortcut to ensure your code matches the project's style:

```bash
make lint
```

### Testing
All contributions require tests to ensure stability and prevent regressions. I use the [pytest](https://pytest.org) framework. 

1. **Write Tests**: Place your tests in the `tests/` directory mirroring the module structure of the codebase.
2. **Run Fast Tests**: Execute the lightweight test suite to ensure everything passes during daily iterations:
   ```bash
   make test-fast
   ```
3. **Run Slow Model Tests**: Before opening a PR, you must verify the full suite with real-model tests enabled. This requires the installed runtime ML dependencies and may download MegaDetector, RT-DETR backbone, and classifier assets on the first run:
   ```bash
   make test
   ```
4. **Test Coverage**: I require a minimum of $\ge 80\%$ code coverage. The default test commands enforce this through the repository configuration automatically.

---

## 📝 Pull Request (PR) Process

### 1. Create a Feature Branch
Avoid making modifications directly to your local [`main`](https://git-scm.com/docs/git-branch) branch. Always run your edits on an isolated feature branch:
```bash
git checkout -b feature/your-feature-name
```

### 2. Pre-Flight Validation
Ensure your [`git`](https://git-scm.com/) branch is clean, up-to-date, linted, and passes local testing before pushing. You can use the dedicated pre-PR shortcut to check all three at once:
```bash
make pr
```

### 3. Commit Messages
Write clear, descriptive commit messages. I encourage using [Conventional Commits](https://conventionalcommits.org), for example:
*   `feat(auth): add JWT token validation`
*   `fix(routes): resolve 500 error on GET /users`

### 4. Push to Your Fork
```bash
git push origin feature/your-feature-name
```

### 5. Open a PR
Go to the main repository and open a Pull Request. Provide a clear summary of your changes, the problem you are solving and your full integration test results. Reference any relevant issue numbers.

### 6. Code Review
Project maintainers will review your code. You may be asked to make adjustments. Once approved and all automated CI checks (linters and tests) pass, your code will be merged!

---

## ❓ Questions or Need Help?
If you have any questions about setting up your environment or need guidance on how to implement a feature, feel free to open a [GitHub Issue](https://github.com/jasondentler/wild-catalog/issues).

## Preop and Testing Workflow

Before running the full integration test suite, prepare durable assets with:

```bash
make preop
```

Do not add new Makefile commands for individual tests. Real-model integration tests should live under `tests/integration/` and run through the existing `make test` behavior. Fast unit and contract tests should use stubs and fakes under `tests/unit/`.

All tests must live under one of these folders:

```text
tests/unit/
tests/integration/
```

Do not create tests directly under `tests/`.

`make clean` may remove generated `data/` assets, including `data/models/`. Re-run `make preop` after cleaning if you need real-model or local-data integration tests.

## Documentation Contributions

When changing code that affects public behavior, update the matching docs in `docs/` and the relevant OpenAPI examples or tests.

Good documentation updates usually include:

* request and response shape changes in `docs/api-layer.md`
* pipeline behavior changes in the stage docs
* new curl examples in `docs/sample-image-curl-commands.md`
* test updates when documented behavior changes

If you are unsure whether a change is public-facing, update the docs alongside the code.

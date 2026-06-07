# Contributing to Wild Catalog

Thank you for your interest in contributing to Wild Catalog. Contributions are welcome, including bug reports, documentation improvements, model plugin adapters, tests, and feature work.

## Getting Started

This assumes you have [`git`](https://git-scm.com/) installed and are comfortable working at the terminal.

### 1. Fork and clone the project

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

### 2. Track the upstream project

```bash
git remote add upstream https://github.com/jasondentler/wild-catalog.git
```

## Environment setup

Wild Catalog uses Python and Make-based shortcuts for local development. The development runtime should stay aligned with the version range in `pyproject.toml`.

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

---

## 💡 Daily Development Shortcuts

Once your environment is built via the initial [`make`](https://www.gnu.org/software/make/) invocation, use these shortcuts for quick local development loops:

*   **`make serve`** — Starts the local [Uvicorn](https://www.uvicorn.org/) API server with live code auto-reload enabled.
*   **`make test-fast`** — Runs lightweight unit tests immediately while skipping heavyweight integration checks.
*   **`make test`** — Runs the full test suite, including end-to-end integration checks.
*   **`make lint`** — Runs code linting checks using [Ruff](https://ruff.rs/).
*   **`make lint-fix`** — Automatically fixes safe code style errors and organizes imports.
*   **`make clean`** — Wipes the `.venv` directory clean if you need to perform a fresh reinstall.

## 🛠️ Development Workflow

### Code Style & Linting

I use [Ruff](https://ruff.rs) to enforce code formatting and catch potential issues. Before committing with [`git`](https://git-scm.com/), run the linter shortcut to ensure your code matches the project's style:

```bash
make lint
```

### Testing
All contributions require tests to ensure stability and prevent regressions. I use the [pytest](https://pytest.org) framework. 

1. **Write Tests**: Place tests under `tests/unit/` or `tests/integration/`, mirroring the module structure below that level.
2. **Run Fast Tests**: Execute the lightweight test suite to ensure everything passes during daily iterations:
   ```bash
   make test-fast
   ```
3. **Run Slow Model Tests**: Before opening a PR, you must verify the full suite with real-model tests enabled. This requires the installed runtime ML dependencies and may download YOLO and Birder model weights on the first run:
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

A proper commit message can be created using [commitizen](https://commitizen-tools.github.io/commitizen/) by running:

```bash
make commit
```

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

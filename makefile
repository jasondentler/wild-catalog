.PHONY: all clean venv install install-hooks license-check lint lint-fix test test-fast check-prereqs serve pr commit preop preop-taxonomy-dwca preop-range-maps preop-classifier-model preop-detector-model

# 1. Detect Operating System and set path/variable rules
ifeq ($(OS),Windows_NT)
    # Windows Settings
    PYTHON_EXE := $(shell where python 2>nul | findstr "3.13")
    XCODE_CHECK := bypassed
    VENV_BIN := .venv/Scripts
    SET_ENV := set WILD_CATALOG_RUN_INTEGRATION_TESTS=1 &&
	RM_RF := rmdir /s /q
else
    # macOS Settings
    PYTHON_EXE := $(shell which python3.13 2>/dev/null)
    XCODE_CHECK := $(shell xcode-select -p 2>/dev/null)
    VENV_BIN := .venv/bin
    SET_ENV := WILD_CATALOG_RUN_INTEGRATION_TESTS=1
    RM_RF := rm -rf
endif

# Default target when you just run 'make'
all: clean venv install install-hooks license-check lint test

# 2. Pre-flight check for system requirements
check-prereqs:
	@if [ "$(XCODE_CHECK)" = "" ]; then \
		echo "=========================================================="; \
		echo "❌ ERROR: Xcode Command Line Tools are not installed."; \
		echo "Please install them by running the following command:"; \
		echo "    xcode-select --install"; \
		echo "=========================================================="; \
		exit 1; \
	fi
	@if [ "$(PYTHON_EXE)" = "" ]; then \
		echo "=========================================================="; \
		echo "❌ ERROR: This project requires Python 3.13."; \
		echo "Please ensure it is installed and available on your PATH."; \
		echo "=========================================================="; \
		exit 1; \
	fi

# 3. Clean old virtual environment
clean:
	-$(RM_RF) .venv
	-$(RM_RF) data

# 4. Create a new virtual environment
venv: check-prereqs
	@echo "Creating venv using: $(PYTHON_EXE)"
	"$(PYTHON_EXE)" -m venv .venv

# 5. Upgrade pip, bundle local uv, and install dependencies safely
install:
	$(VENV_BIN)/python -m pip install --upgrade pip "setuptools<82" wheel
	$(VENV_BIN)/python -m pip install uv
	$(VENV_BIN)/uv pip install -e ".[dev]"

install-hooks:
	$(VENV_BIN)/pre-commit install --hook-type commit-msg

license-check:
	$(VENV_BIN)/licensecheck --license Apache-2.0 --zero --show-only-failing
	
# 6. Lint everything using Ruff
lint:
	$(VENV_BIN)/ruff check .

# 6b. Automatically fix linting and formatting issues using Ruff
lint-fix:
	$(VENV_BIN)/ruff check . --fix

# 7. Run ALL tests (including full integration tests)
test:
	$(SET_ENV) $(VENV_BIN)/pytest

# 8. Run fast unit tests only (skips heavy integration checks)
test-fast:
	$(VENV_BIN)/pytest

# 9. Start the local development API server with auto-reload
serve:
	$(VENV_BIN)/uvicorn wild_catalog.api.app:app --reload --log-level debug --app-dir src

# 9b. Run pre-operational setup tasks
preop:
	$(VENV_BIN)/python -m wild_catalog.preop.cli

preop-taxonomy-dwca:
	$(VENV_BIN)/python -m wild_catalog.taxonomy.preop

preop-range-maps:
	$(VENV_BIN)/python -m wild_catalog.prior.build.cli

preop-classifier-model:
	$(VENV_BIN)/python -m wild_catalog.classifier.preop

preop-detector-model:
	$(VENV_BIN)/python -m wild_catalog.detection.preop

# 10. Pre-PR Validation checklist (Runs updates, linter, and tests)
pr: install lint test
	@echo "=========================================================="
	@echo "✅ SUCCESS: Code looks good! Ready to push your branch."
	@echo "=========================================================="

# 11. For commit messages, use commitizen 
commit:
	$(VENV_BIN)/cz commit

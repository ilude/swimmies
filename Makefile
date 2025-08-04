# Swimmies Library Development Makefile
# Standalone development commands for swimmies utility library

.PHONY: help install test lint format clean type-check coverage example dev-install publish build

# Default target
help: ## Show this help message
	@echo "Swimmies Library Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Install dependencies (only if pyproject.toml changed)
uv.lock: pyproject.toml
	uv sync --extra dev
	@touch uv.lock

install: uv.lock ## Install development dependencies
	@echo "✅ Development dependencies installed"

dev-install: uv.lock ## Install in development mode (editable)
	uv sync --extra dev
	@echo "✅ Swimmies installed in development mode"

# Run tests with coverage
test: uv.lock ## Run tests with coverage report
	@echo "Running swimmies tests with coverage..."
	uv run pytest tests/ --cov=swimmies --cov-report=term-missing --cov-report=html:.htmlcov -v
	@echo "✅ Tests completed!"

# Run tests without coverage (faster)
test-fast: uv.lock ## Run tests without coverage (faster)
	@echo "Running swimmies tests..."
	uv run pytest tests/ -v
	@echo "✅ Tests completed!"

# Run specific test file
test-discovery: uv.lock ## Run only discovery module tests
	@echo "Running discovery tests..."
	uv run pytest tests/test_discovery.py -v
	@echo "✅ Discovery tests completed!"

test-core: uv.lock ## Run only core module tests
	@echo "Running core tests..."
	uv run pytest tests/test_core.py -v
	@echo "✅ Core tests completed!"

test-gossip: uv.lock ## Run only gossip module tests
	@echo "Running gossip tests..."
	uv run pytest tests/test_gossip.py -v
	@echo "✅ Gossip tests completed!"

# Run linting
# E203: whitespace before ':' (conflicts with black formatting)
# W503: line break before binary operator (conflicts with black formatting)
# E501: line too long (disabled to match black's line length handling)
lint: uv.lock ## Run code linting
	@echo "Running flake8 linting..."
	uv run flake8 src tests --extend-ignore=E203,W503,E501
	@echo "✅ Linting completed successfully!"

# Format code
format: uv.lock ## Format code with black and isort
	@echo "Formatting code with black..."
	uv run black src/ tests/ examples/
	@echo "Organizing imports with isort..."
	uv run isort src/ tests/ examples/ --profile black
	@echo "Removing trailing whitespace..."
	find src tests examples -name "*.py" -exec sed -i 's/[[:space:]]*$$//' {} \; 2>/dev/null || true
	@echo "✅ Code formatting completed!"

# Type checking (if mypy is added later)
type-check: uv.lock ## Run type checking (requires mypy)
	@echo "Type checking not yet configured. Add mypy to dev dependencies to enable."

# Coverage report
coverage: uv.lock ## Generate detailed coverage report
	@echo "Generating coverage report..."
	uv run pytest tests/ --cov=swimmies --cov-report=html:.htmlcov --cov-report=term
	@echo "✅ Coverage report generated in .htmlcov/"

# Run example script
example: uv.lock ## Run the discovery example
	@echo "Running discovery example..."
	@echo "Press Ctrl+C to stop..."
	uv run python examples/discovery_example.py

# Clean Python cache files and build artifacts
clean: ## Clean cache files and build artifacts
	@echo "Cleaning Python cache files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage .htmlcov/ .pytest_cache/ dist/ build/
	@echo "✅ Clean completed!"

# Build package
build: uv.lock ## Build distribution packages
	@echo "Building swimmies package..."
	uv build
	@echo "✅ Package built in dist/"

# Quality check (combines linting, formatting check, and tests)
check: uv.lock ## Run all quality checks (lint, format check, tests)
	@echo "Running quality checks..."
	@echo "1/3 - Checking code formatting..."
	uv run black --check src/ tests/ examples/
	uv run isort --check-only src/ tests/ examples/ --profile black
	@echo "2/3 - Running linting..."
	uv run flake8 src tests --extend-ignore=E203,W503,E501
	@echo "3/3 - Running tests..."
	uv run pytest tests/ -v
	@echo "✅ All quality checks passed!"

# Development setup
setup: ## Complete development setup
	@echo "Setting up swimmies development environment..."
	uv sync --extra dev
	@echo ""
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "Available commands:"
	@$(MAKE) --no-print-directory help

# Watch mode for tests (requires entr or similar)
watch: uv.lock ## Watch for changes and run tests (requires 'entr')
	@echo "Watching for changes... (Press Ctrl+C to stop)"
	@echo "Requires 'entr' command: apt-get install entr"
	find src tests -name "*.py" | entr -c make test-fast

# Show project info
info: ## Show project information
	@echo "Swimmies Library Information:"
	@echo "  Version: $$(uv run python -c 'import swimmies; print(swimmies.__version__)')"
	@echo "  Python: $$(python3 --version)"
	@echo "  UV: $$(uv --version)"
	@echo "  Dependencies: $$(uv run pip list | wc -l) packages"
	@echo "  Test files: $$(find tests -name '*.py' | wc -l)"
	@echo "  Source files: $$(find src -name '*.py' | wc -l)"

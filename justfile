# Maho development tasks

# Default recipe to display available commands
default:
    @just --list

# Install dependencies using uv
install:
    uv sync

# Install development dependencies
install-dev:
    uv sync --dev

# Run the web UI server
ui:
    uv run scripts/start_ui.py

# Run the tunnel server
tunnel:
    uv run scripts/start_tunnel.py

# Prepare the environment (SSH passwords, etc.)
prepare:
    uv run scripts/prepare.py

# Preload models
preload:
    uv run scripts/preload.py

# Format code with black
fmt:
    uv run black src/ scripts/

# Lint code with ruff
lint:
    uv run ruff check src/ scripts/

# Fix linting issues automatically
lint-fix:
    uv run ruff check --fix src/ scripts/

# Type check with mypy
typecheck:
    uv run mypy src/

# Run all quality checks
check: lint typecheck

# Clean up Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete

# Build Docker image
docker-build:
    docker build -t maho:latest -f docker/run/Dockerfile .

# Run Docker container
docker-run:
    docker run -p 50080:80 -v $(pwd):/a0 maho:latest

# Docker compose up
docker-up:
    cd docker/run && docker-compose up

# Docker compose down
docker-down:
    cd docker/run && docker-compose down

# Update dependencies to latest versions
update:
    uv lock --upgrade

# Show dependency tree
deps:
    uv tree

# Run a shell with the virtual environment activated
shell:
    uv shell

# Install pre-commit hooks
setup-hooks:
    uv run pre-commit install

# Run tests (when we add them)
test:
    uv run pytest

# Generate requirements.txt for legacy compatibility (if needed)
export-reqs:
    uv export --format requirements-txt --output-file requirements.txt

# Show project info
info:
    @echo "Maho - Refactored Agent Zero"
    @echo "Python: $(python --version)"
    @echo "UV: $(uv --version)"
    @uv tree --depth 1 
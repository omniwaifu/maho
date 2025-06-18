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

# Type check with pyright
typecheck:
    uv run pyright src/

# Run all quality checks
check: lint typecheck

# Clean up Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete

# Build Docker image (simple, no Agent Zero dependencies)
docker-build:
    docker build -t maho:latest -f docker/run/Dockerfile.simple .

# Build Docker image (complex, with Agent Zero base - if you really want it)
docker-build-complex:
    docker build -t maho:latest -f docker/run/Dockerfile --build-arg BRANCH=main .

# Run Docker container (production mode - mounts data to ~/.config/maho)
docker-run:
    mkdir -p ~/.config/maho/{memory,logs,tmp,knowledge,work_dir}
    docker run -p 50080:80 \
        -v ~/.config/maho/memory:/maho/memory \
        -v ~/.config/maho/logs:/maho/logs \
        -v ~/.config/maho/tmp:/maho/tmp \
        -v ~/.config/maho/knowledge:/maho/knowledge \
        -v ~/.config/maho/work_dir:/root \
        maho:latest

# Run Docker container for testing (ephemeral - auto-removes on exit)
docker-test:
    mkdir -p ~/.config/maho/{memory,logs,tmp,knowledge,work_dir}
    docker run --rm -it --init -p 50080:80 \
        --env-file .env \
        -v ~/.config/maho/memory:/maho/memory \
        -v ~/.config/maho/logs:/maho/logs \
        -v ~/.config/maho/tmp:/maho/tmp \
        -v ~/.config/maho/knowledge:/maho/knowledge \
        -v ~/.config/maho/work_dir:/root \
        maho:latest

# Run Docker container in development mode (mounts entire codebase)
docker-dev:
    docker run -p 50080:80 -v $(pwd):/maho maho:latest

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

# Clean up maho Docker images and containers
docker-clean:
    docker container prune -f
    docker image rm maho:latest || true
    docker system prune -f 
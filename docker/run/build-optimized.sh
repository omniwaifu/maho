#!/bin/bash

# Optimized Docker build script for Maho
# Uses multi-stage builds with aggressive caching to minimize rebuild times

set -e

# Configuration
IMAGE_NAME="maho"
DOCKERFILE="docker/run/Dockerfile.simple"
BUILD_CONTEXT="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting optimized Maho build...${NC}"

# Build arguments
BRANCH=${1:-main}
CACHE_DATE=$(date +%s)

echo -e "${YELLOW}📦 Building with branch: $BRANCH${NC}"

# Build with BuildKit for better caching
export DOCKER_BUILDKIT=1

# Build the image with stage caching
docker build \
    --file "$DOCKERFILE" \
    --build-arg BRANCH="$BRANCH" \
    --build-arg CACHE_DATE="$CACHE_DATE" \
    --target runtime \
    --tag "$IMAGE_NAME:latest" \
    --tag "$IMAGE_NAME:$BRANCH" \
    "$BUILD_CONTEXT"

echo -e "${GREEN}✅ Build completed successfully!${NC}"
echo -e "${BLUE}📊 Image details:${NC}"
docker images "$IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo -e "${YELLOW}💡 Pro tips for faster rebuilds:${NC}"
echo -e "  • Only the final stage rebuilds when you change code"
echo -e "  • Dependencies are cached in earlier stages"
echo -e "  • Use 'docker system prune -f' to clean up old layers"
echo -e "  • Heavy assets (models, browsers) are cached separately"

echo -e "${GREEN}🎉 Ready to run with: docker run -it $IMAGE_NAME:latest${NC}" 
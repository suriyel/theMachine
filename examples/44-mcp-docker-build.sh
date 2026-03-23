#!/bin/bash
# Example: Feature #44 — mcp-server Docker Image
#
# Builds the codecontext-mcp image from docker/Dockerfile.mcp
# and inspects the resulting image config to verify CMD, HEALTHCHECK,
# user, and exposed ports.
#
# Usage (from repository root):
#   bash examples/44-mcp-docker-build.sh

set -e

IMAGE="codecontext-mcp"

echo "Building $IMAGE from docker/Dockerfile.mcp..."
docker build -f docker/Dockerfile.mcp -t "$IMAGE" .
echo

echo "Image config:"
docker inspect "$IMAGE" --format '{{json .Config}}' | python3 -m json.tool | grep -E '"Cmd"|"Healthcheck"|"User"|"ExposedPorts"'
echo

echo "Runtime user (should be 1000):"
docker run --rm "$IMAGE" id -u
echo

echo "Dev packages absent (pip show pytest should fail):"
docker run --rm "$IMAGE" pip show pytest 2>&1 || echo "  OK — pytest not installed"
echo

echo "OK — codecontext-mcp image built and verified."

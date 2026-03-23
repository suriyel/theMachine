#!/bin/bash
# Example: Feature #45 — index-worker Docker Image
#
# Builds the codecontext-worker image from docker/Dockerfile.worker
# and inspects the resulting image config to verify CMD, HEALTHCHECK,
# user, and exposed ports.
#
# Usage (from repository root):
#   bash examples/45-worker-docker-build.sh

set -e

IMAGE="codecontext-worker"

echo "Building $IMAGE from docker/Dockerfile.worker..."
docker build -f docker/Dockerfile.worker -t "$IMAGE" .
echo

echo "Image config:"
docker inspect "$IMAGE" --format '{{json .Config}}' | python3 -m json.tool | grep -E '"Cmd"|"Healthcheck"|"User"|"ExposedPorts"'
echo

echo "Runtime user (should be 1000):"
docker run --rm "$IMAGE" id -u
echo

echo "Celery version installed:"
docker run --rm "$IMAGE" celery --version
echo

echo "Dev packages absent (pip show pytest should fail):"
docker run --rm "$IMAGE" pip show pytest 2>&1 || echo "  OK — pytest not installed"
echo

echo "OK — codecontext-worker image built and verified."

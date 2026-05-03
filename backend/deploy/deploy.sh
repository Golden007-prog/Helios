#!/usr/bin/env bash
# Build and push the backend image, then apply the Code Engine spec.
#
# Usage:
#   IMAGE_TAG=$(git rev-parse --short HEAD) ./backend/deploy/deploy.sh
#
# Required env: IBM_CLOUD_API_KEY, IBM_CLOUD_REGION, IMAGE_TAG.
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-icr.io/helios/helios-backend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo ">> Logging into IBM Container Registry"
ibmcloud login --apikey "${IBM_CLOUD_API_KEY}" -r "${IBM_CLOUD_REGION:-us-south}"
ibmcloud cr login

echo ">> Building image ${IMAGE_NAME}:${IMAGE_TAG}"
docker build \
    --build-arg HELIOS_GIT_SHA="${GIT_SHA}" \
    --build-arg HELIOS_BUILD_TIME="${BUILD_TIME}" \
    --build-arg HELIOS_IMAGE_TAG="${IMAGE_TAG}" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    backend

echo ">> Pushing image"
docker push "${IMAGE_NAME}:${IMAGE_TAG}"

echo ">> Applying Code Engine app"
IMAGE_TAG="${IMAGE_TAG}" envsubst < backend/deploy/code-engine.yaml \
    | ibmcloud ce app apply --file -

echo ">> Done. URL:"
ibmcloud ce app get -n helios-backend -o url

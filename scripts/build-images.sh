#!/usr/bin/env bash
set -euo pipefail

buildah bud -f proof-service/Containerfile -t sealium/proof-service:dev .
buildah bud -f transcription-service/Containerfile -t sealium/transcription-service:dev .

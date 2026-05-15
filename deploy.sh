#!/usr/bin/env bash
set -euo pipefail

# Ensure we run from repository root if invoked from elsewhere
cd "$(dirname "$0")" || exit 1

echo "[deploy] pulling latest changes"
git pull origin main

echo "[deploy] building and starting containers"
docker compose up -d --build --remove-orphans

echo "[deploy] SUCCESS"
exit 0
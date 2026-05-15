#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[deploy] FAILED"' ERR

# Ensure we run from repository root if invoked from elsewhere
cd "$(dirname "$0")" || exit 1

echo "[deploy] current commit: $(git rev-parse --short HEAD)"

echo "[deploy] syncing with origin/main"
git fetch origin main
git reset --hard origin/main
git clean -fd

echo "[deploy] synced commit: $(git rev-parse --short HEAD)"

echo "[deploy] building and starting containers"
COMPOSE_ARGS=(-p slevobot)

if [[ -x /usr/bin/sudo ]]; then
	/usr/bin/sudo -n /usr/bin/docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans || true
	/usr/bin/sudo -n /usr/bin/docker compose "${COMPOSE_ARGS[@]}" up -d --build --force-recreate --remove-orphans
elif command -v sudo >/dev/null 2>&1; then
	sudo -n /usr/bin/docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans || true
	sudo -n /usr/bin/docker compose "${COMPOSE_ARGS[@]}" up -d --build --force-recreate --remove-orphans
elif ! command -v docker >/dev/null 2>&1; then
	echo "[deploy] docker is not installed or not in PATH"
	exit 1
else
	docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans || true
	docker compose "${COMPOSE_ARGS[@]}" up -d --build --force-recreate --remove-orphans
fi

echo "[deploy] SUCCESS"
exit 0
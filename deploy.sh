#!/usr/bin/env bash
set -e

git pull origin main
docker compose up -d --build --remove-orphans
#!/bin/bash
# Atualiza o servidor na VPS: código novo do git + yt-dlp mais recente.
# Rode quando os downloads começarem a falhar (o YouTube mudou algo).
set -e
cd "$(dirname "$0")/.."
git pull
docker compose build --pull --no-cache server
docker compose up -d
docker compose exec server yt-dlp --version

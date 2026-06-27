#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_BUNDLE="$ROOT_DIR/dist/pku_simulator.app"

if [[ ! -d "$APP_BUNDLE" ]]; then
  echo "[ERROR] App bundle not found: $APP_BUNDLE"
  echo "[INFO] Please build first: ./scripts/build_executable.sh"
  exit 1
fi

open "$APP_BUNDLE"
echo "[DONE] Opened: $APP_BUNDLE"
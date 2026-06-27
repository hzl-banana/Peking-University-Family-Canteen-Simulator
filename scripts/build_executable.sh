#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

APP_COVER_IMAGE="assets/generated/start_cover.png"
MAC_ICON_PATH="build/app_icon.icns"

if ! python - <<'PY'
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("PyInstaller") else 1)
PY
then
  echo "[INFO] PyInstaller not found in current Python env, installing..."
  python -m pip install pyinstaller
fi

# Ensure project runtime dependencies exist in the active Python env.
python -m pip install -e .

if ! python - <<'PY'
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("PySide6") else 1)
PY
then
  echo "[INFO] PySide6 not found, installing..."
  python -m pip install "PySide6>=6.7,<7.0"
fi

if [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* || "${OSTYPE:-}" == win32* ]]; then
  SEP=';'
  EXE_NAME='pku_simulator.exe'
else
  SEP=':'
  EXE_NAME='pku_simulator'
fi

ICON_ARGS=()
if [[ "${OSTYPE:-}" == darwin* && -f "$APP_COVER_IMAGE" ]]; then
  if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
    ICONSET_DIR="build/app_icon.iconset"
    mkdir -p "$ICONSET_DIR"

    for size in 16 32 128 256 512; do
      sips -s format png -z "$size" "$size" "$APP_COVER_IMAGE" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
      retina_size=$((size * 2))
      sips -s format png -z "$retina_size" "$retina_size" "$APP_COVER_IMAGE" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
    done

    iconutil -c icns "$ICONSET_DIR" -o "$MAC_ICON_PATH"
    ICON_ARGS=(--icon "$MAC_ICON_PATH")
    echo "[INFO] macOS icon generated from $APP_COVER_IMAGE"
  else
    echo "[WARN] sips/iconutil unavailable, skip app icon generation."
  fi
fi

python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name pku_simulator \
  --collect-all PySide6 \
  --collect-all shiboken6 \
  --hidden-import PySide6.QtCore \
  --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtMultimedia \
  --hidden-import PySide6.QtWidgets \
  --add-data "assets${SEP}assets" \
  --add-data "bgm${SEP}bgm" \
  "${ICON_ARGS[@]}" \
  src/pku_simulator/main.py

echo "[DONE] Build complete: dist/pku_simulator/${EXE_NAME}"

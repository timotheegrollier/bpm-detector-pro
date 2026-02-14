#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
VENV="$ROOT/.venv-build"

if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
echo "Sync version from git tag..."
python "$ROOT/scripts/update_version.py" || echo "WARNING: update_version.py failed, using existing version"
python -m pip install --upgrade pip
# Default to optimized build unless USE_LEGACY_BUILD is set
USE_OPTIMIZED=true
if [ "${USE_LEGACY_BUILD:-0}" = "1" ]; then
  USE_OPTIMIZED=false
fi

echo "=== BPM Detector Pro - Linux Build ==="
if [ "$USE_OPTIMIZED" = true ]; then
  echo "Mode: OPTIMIZED (fast startup, small size)"
else
  echo "Mode: Legacy (full librosa)"
fi

if [ ! -d "$VENV" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
echo "Installing dependencies..."
python -m pip install --upgrade pip --quiet

if [ "$USE_OPTIMIZED" = true ]; then
  pip install -r "$ROOT/requirements-minimal.txt" pyinstaller --quiet
else
  pip install -r "$ROOT/requirements.txt" pyinstaller --quiet
fi

FFMPEG_BIN="${FFMPEG_BINARY:-}"
if [ -z "$FFMPEG_BIN" ]; then
  CAND="$ROOT/packaging/ffmpeg/linux/ffmpeg"
  if [ -f "$CAND" ]; then
    FFMPEG_BIN="$CAND"
  fi
fi

if [ -z "$FFMPEG_BIN" ]; then
  echo "ffmpeg introuvable. Place-le dans packaging/ffmpeg/linux/ffmpeg ou definis FFMPEG_BINARY." >&2
  exit 1
fi

# Fix permissions for libraries that PyInstaller needs to scan
find "$VENV" -name "*.so*" -exec chmod +x {} + 2>/dev/null || true

if [ -f "$FFMPEG_BIN" ]; then
  chmod +x "$FFMPEG_BIN"
fi

SPEC_FILE="$ROOT/bpm-detector.spec"
if [ "$USE_OPTIMIZED" = true ]; then
  if [ -f "$ROOT/bpm-detector-optimized.spec" ]; then
    SPEC_FILE="$ROOT/bpm-detector-optimized.spec"
  else
    echo "Optimized spec not found, using legacy..."
    SPEC_FILE="$ROOT/bpm-detector.spec"
  fi
fi

# UPX (optional). Disabled by default on Linux to avoid breaking shared libs.
UPX_ARGS=""
if [ "${USE_UPX:-0}" = "1" ]; then
  UPX_DIR="$ROOT/tools/upx-linux"
  UPX_BIN="$UPX_DIR/upx"

  if [ ! -f "$UPX_BIN" ]; then
    echo "Downloading UPX for Linux..."
    mkdir -p "$UPX_DIR"
    curl -L "https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-amd64_linux.tar.xz" -o upx.tar.xz
    tar xf upx.tar.xz
    mv upx-*-amd64_linux/upx "$UPX_BIN"
    rm -rf upx.tar.xz upx-*-amd64_linux
    chmod +x "$UPX_BIN"
    echo "UPX installed."
  fi

  if [ -f "$UPX_BIN" ]; then
    UPX_ARGS="--upx-dir=$UPX_DIR"
    echo "Using UPX compression."
  fi
fi

echo "Building with: $SPEC_FILE"

# Build
pyinstaller --noconfirm --clean \
  --distpath "$ROOT/dist" \
  --workpath "$ROOT/build" \
  $UPX_ARGS \
  "$SPEC_FILE"

# Post-processing optimization (strip disabled by default on Linux)
OUTPUT_BIN="$ROOT/dist/BPM-Detector-Pro"
if [ -f "$OUTPUT_BIN" ] && [ "$USE_OPTIMIZED" = true ]; then
  if [ "${USE_STRIP:-0}" = "1" ]; then
    echo "Stripping binary symbols..."
    strip -s "$OUTPUT_BIN" || true
  fi
  
  SIZE=$(du -h "$OUTPUT_BIN" | cut -f1)
  echo "Final Binary Size: $SIZE"
fi

echo "OK -> $OUTPUT_BIN"

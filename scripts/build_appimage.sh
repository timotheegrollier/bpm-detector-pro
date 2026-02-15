#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/scripts/build_linux.sh"

APPDIR="$ROOT/dist/AppDir"
ARCH="$(uname -m)"
OUT="$ROOT/dist/BPM-detector-${ARCH}.AppImage"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/icons/hicolor/scalable/apps"

cp "$ROOT/dist/BPM-detector" "$APPDIR/usr/bin/bpm-detector"
cp "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"
cp "$ROOT/packaging/appimage/bpm-detector.desktop" "$APPDIR/bpm-detector.desktop"
cp "$ROOT/packaging/assets/bpm-detector.svg" \
  "$APPDIR/usr/share/icons/hicolor/scalable/apps/bpm-detector.svg"
cp "$ROOT/packaging/assets/bpm-detector.svg" "$APPDIR/bpm-detector.svg"

chmod +x "$APPDIR/AppRun"

if ! command -v appimagetool >/dev/null 2>&1; then
  echo "appimagetool introuvable. Installe-le puis relance ce script." >&2
  echo "AppDir pret: $APPDIR" >&2
  exit 1
fi

appimagetool "$APPDIR" "$OUT"

echo "OK -> $OUT"

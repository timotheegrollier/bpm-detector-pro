#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/packaging/flatpak/com.bpm.Detector.yml"
BUILD_DIR="$ROOT/dist/flatpak-build"
REPO_DIR="$ROOT/dist/flatpak-repo"
BUNDLE="$ROOT/dist/BPM-detector.flatpak"

if ! command -v flatpak-builder >/dev/null 2>&1; then
  echo "flatpak-builder introuvable. Installe flatpak-builder puis relance." >&2
  exit 1
fi

mkdir -p "$ROOT/dist"

flatpak-builder --force-clean --repo="$REPO_DIR" "$BUILD_DIR" "$MANIFEST"
flatpak build-bundle "$REPO_DIR" "$BUNDLE" com.bpm.Detector \
  --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo

echo "OK -> $BUNDLE"

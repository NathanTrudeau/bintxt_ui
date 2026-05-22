#!/usr/bin/env bash
# bintxt_ui Linux/macOS build script
# Requires: pip install pyinstaller
# Output:   dist/bintxt_ui

set -euo pipefail

echo "[bintxt_ui] Building executable..."

git submodule update --init --recursive

rm -rf build dist

pyinstaller bintxt_ui.spec

echo ""
echo "[bintxt_ui] Build complete: dist/bintxt_ui"

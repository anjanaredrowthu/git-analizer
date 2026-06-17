#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/package"

rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/scripts"

python -m pip install --upgrade pip
python -m pip install -r "$SCRIPT_DIR/../requirements.txt" -t "$PACKAGE_DIR"

cp "$SCRIPT_DIR/lambda_function.py" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/../scripts/analyze_repos.py" "$PACKAGE_DIR/scripts/"

find "$PACKAGE_DIR" -type f -name '*.pyc' -delete

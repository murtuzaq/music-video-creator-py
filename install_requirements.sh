#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pip install -r "$SCRIPT_DIR/requirements.txt"
pip install -r "$SCRIPT_DIR/tools/audioasset-creator/requirements.txt"

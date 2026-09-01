#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$SCRIPT_DIR/.venv/bin/python3" ]; then
    exec "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/launcher.py"
fi
exec python3 "$SCRIPT_DIR/launcher.py"

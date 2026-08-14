#!/usr/bin/env bash
# Launch the sudoku solver.
set -euo pipefail

cd "$(dirname "$0")"

VENV=${VENV:-.venv}

if [ ! -x "$VENV/bin/python" ]; then
    echo "virtualenv not found -- run ./setup.sh first" >&2
    exit 1
fi

exec "$VENV/bin/python" main.py "$@"

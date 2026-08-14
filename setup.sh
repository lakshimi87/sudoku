#!/usr/bin/env bash
# Create a local virtualenv and install dependencies (pygame-ce).
set -euo pipefail

cd "$(dirname "$0")"

PYTHON=${PYTHON:-python3}
VENV=${VENV:-.venv}

if [ ! -d "$VENV" ]; then
    echo "creating virtualenv in $VENV"
    "$PYTHON" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r requirements.txt

echo
echo "setup done -- run ./play.sh to start"

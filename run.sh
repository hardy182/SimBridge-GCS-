#!/usr/bin/env bash
# SimBridge GCS Launch Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ ! -d ".venv" ]; then
    echo "[ERROR] Virtual environment .venv not found. Please run ./setup.sh first." >&2
    exit 1
fi

source .venv/bin/activate

# Allow passing custom host/port or arguments
HOST="${SIMBRIDGE_HOST:-127.0.0.1}"
PORT="${SIMBRIDGE_PORT:-8050}"

echo "=========================================================="
echo "          Starting SimBridge GCS Dashboard                "
echo "=========================================================="
echo "  Web UI: http://${HOST}:${PORT}"
echo "  API Docs: http://${HOST}:${PORT}/docs"
echo "=========================================================="

exec python3 -m simbridge.cli --host "${HOST}" --port "${PORT}" "$@"

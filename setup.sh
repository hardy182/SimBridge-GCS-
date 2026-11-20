#!/usr/bin/env bash
# SimBridge GCS Environment Setup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "=========================================================="
echo "          SimBridge GCS Environment Setup                 "
echo "=========================================================="

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 is required but not installed." >&2
    exit 1
fi

PYTHON_VER=$(python3 --version 2>&1)
echo "[INFO] Detected ${PYTHON_VER}"

# Create virtual environment if missing
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating dedicated virtual environment in .venv..."
    python3 -m venv .venv
else
    echo "[INFO] Existing virtual environment found in .venv."
fi

# Activate virtual environment
source .venv/bin/activate
echo "[INFO] Upgrading pip..."
pip install --upgrade pip setuptools wheel --quiet

echo "[INFO] Installing SimBridge GCS dependencies..."
pip install -r requirements.txt --quiet

echo "[INFO] Installing SimBridge GCS in editable mode..."
pip install -e . --no-deps --quiet

# Check for environment tools
echo "----------------------------------------------------------"
echo "Checking external simulation tools:"
if command -v gz &>/dev/null; then
    GZ_VER=$(gz --version 2>/dev/null || echo "detected")
    echo "  [FOUND] Gazebo: ${GZ_VER}"
else
    echo "  [OPTIONAL] Gazebo (gz) not found in PATH."
fi

if command -v blender &>/dev/null; then
    BLENDER_VER=$(blender --version 2>/dev/null | head -n 1)
    echo "  [FOUND] Blender: ${BLENDER_VER}"
else
    echo "  [OPTIONAL] Blender not found in PATH."
fi

if [ -d "${HOME}/PX4-Autopilot" ]; then
    echo "  [FOUND] PX4-Autopilot directory at ${HOME}/PX4-Autopilot"
else
    echo "  [OPTIONAL] PX4-Autopilot not detected in ${HOME}/PX4-Autopilot."
fi
echo "----------------------------------------------------------"

echo "[SUCCESS] SimBridge GCS setup complete."
echo "Run './run.sh' to launch the dashboard."

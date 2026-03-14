#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_VERSION="3.11"
VENV_DIR=".venv"

echo "=== Code Context Retrieval — Environment Bootstrap ==="

# --- Step 1: Detect Python ---
PYTHON_BIN=""
for candidate in "python${PYTHON_VERSION}" "python3.11" "python3" "python"; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON_BIN="$candidate"
        break
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: Python not found. Install Python >= ${PYTHON_VERSION}"
    echo "  Download: https://www.python.org/downloads/"
    exit 1
fi

# Version check
ACTUAL_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Found Python ${ACTUAL_VERSION} at $(command -v $PYTHON_BIN)"

if [[ "$(echo "$ACTUAL_VERSION" | cut -d. -f1)" -lt 3 ]] || \
   [[ "$(echo "$ACTUAL_VERSION" | cut -d. -f1)" -eq 3 && "$(echo "$ACTUAL_VERSION" | cut -d. -f2)" -lt 11 ]]; then
    echo "ERROR: Python version must be >= 3.11. Found ${ACTUAL_VERSION}"
    exit 1
fi

# --- Step 2: Create virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_BIN -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# --- Step 3: Activate environment ---
source "${VENV_DIR}/bin/activate"

# --- Step 4: Upgrade pip ---
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# --- Step 5: Install dependencies ---
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt --quiet
fi

if [ -f "requirements-dev.txt" ]; then
    echo "Installing dev dependencies from requirements-dev.txt..."
    pip install -r requirements-dev.txt --quiet
fi

# --- Step 6: Install dev tools ---
echo "Installing development tools..."
pip install pytest pytest-cov mutmut --quiet

# --- Step 7: Verify ---
echo ""
echo "=== Environment Check ==="
echo "python:   $(python --version)"
echo "pip:      $(pip --version | cut -d' ' -f1-2)"
echo "pytest:   $(pytest --version 2>&1 | head -1)"
echo "coverage: $(python -c "import coverage; print(f'coverage {coverage.__version__}')" 2>/dev/null || echo 'not installed')"
echo ""
echo "Environment ready."
echo "Run: source ${VENV_DIR}/bin/activate"

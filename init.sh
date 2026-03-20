#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Code Context Retrieval — Environment Bootstrap ==="

# --- Step 1: Python version check ---
REQUIRED_PYTHON="3.11"
echo ""
echo "--- Step 1: Checking Python version ---"

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found. Please install Python >= $REQUIRED_PYTHON"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "ERROR: Python >= $REQUIRED_PYTHON required, found $PYTHON_VERSION"
    exit 1
fi
echo "Found Python $PYTHON_VERSION ✓"

# --- Step 2: Virtual environment creation ---
echo ""
echo "--- Step 2: Creating virtual environment ---"

if [ -d ".venv" ]; then
    echo "Virtual environment already exists at .venv ✓"
else
    $PYTHON_CMD -m venv .venv
    echo "Created virtual environment at .venv ✓"
fi

# --- Step 3: Activate environment ---
echo ""
echo "--- Step 3: Activating environment ---"
source .venv/bin/activate
echo "Activated .venv ✓"

# --- Step 4: Upgrade pip and install dependencies ---
echo ""
echo "--- Step 4: Installing dependencies ---"

pip install --upgrade pip setuptools wheel --quiet

# Install PyTorch CPU-only first (avoids 2GB+ CUDA download)
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu --quiet

# Install project in editable mode with all dependencies
if [ -f "pyproject.toml" ]; then
    pip install -e ".[dev]" --quiet
    echo "Installed project with dev dependencies ✓"
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt --quiet
    fi
    echo "Installed requirements ✓"
else
    echo "WARNING: No pyproject.toml or requirements.txt found"
fi

# --- Step 5: Install dev tools ---
echo ""
echo "--- Step 5: Verifying dev tools ---"

# Ensure pytest, pytest-cov, mutmut are available
pip install pytest pytest-cov pytest-asyncio mutmut --quiet
echo "Dev tools installed ✓"

# --- Step 6: Database migrations ---
echo ""
echo "--- Step 6: Checking Alembic migrations ---"
if [ -f "alembic.ini" ]; then
    echo "Alembic config found ✓ (run 'alembic upgrade head' when database is available)"
else
    echo "No alembic.ini found (will be created during feature implementation)"
fi

# --- Step 7: Create .env from example if missing ---
echo ""
echo "--- Step 7: Checking .env ---"
if [ -f ".env" ]; then
    echo ".env file exists ✓"
elif [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created .env from .env.example — please fill in the values"
else
    echo "No .env or .env.example found (will be created during initialization)"
fi

# --- Step 8: Verify ---
echo ""
echo "=== Environment Check ==="
echo "Python:           $(python --version)"
echo "pip:              $(pip --version | cut -d' ' -f1-2)"
echo "pytest:           $(pytest --version 2>/dev/null | head -1 || echo 'not installed')"
echo "mutmut:           $(mutmut version 2>/dev/null || echo 'not installed')"
echo "alembic:          $(alembic --version 2>/dev/null | head -1 || echo 'not installed')"

echo ""
echo "=== Environment ready. ==="
echo ""
echo "To activate in your shell:"
echo "  source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest --cov=src --cov-branch --cov-report=term-missing tests/"

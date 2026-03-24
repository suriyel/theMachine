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

# --- Step 6: Patch mutmut 3.2.0 known issues ---
echo ""
echo "--- Step 6: Patching mutmut 3.2.0 ---"

MUTMUT_MAIN=".venv/lib/python3.12/site-packages/mutmut/__main__.py"
if [ -f "$MUTMUT_MAIN" ]; then
    PATCHED=0

    # Patch 1: strip_prefix('src.') breaks src-as-package projects.
    # mutmut strips the 'src.' prefix from module names derived from file paths,
    # causing a mismatch with the actual module names (which start with 'src.').
    # Fix: remove the strip_prefix call so the file-path-derived name keeps 'src.'.
    if grep -q "strip_prefix(str(filename)" "$MUTMUT_MAIN"; then
        sed -i "s|module_name = strip_prefix(str(filename)\[:-len(filename.suffix)\].replace(os.sep, '.'), prefix='src.')|module_name = str(filename)[:-len(filename.suffix)].replace(os.sep, '.')|" "$MUTMUT_MAIN"
        PATCHED=$((PATCHED + 1))
        echo "  Patch 1 applied: strip_prefix removal ✓"
    else
        echo "  Patch 1 already applied ✓"
    fi

    # Patch 2: KeyError on third-party __init__ in stats collection.
    # When pytest collects stats, functions from third-party packages appear in
    # mutmut._stats but not in tests_by_mangled_function_name, causing KeyError.
    # Fix: guard with 'if function in' check (matches the hammett runner pattern).
    # Detection: the StatsCollector class has the unguarded .add() if it does NOT
    # contain 'if function in mutmut.tests_by_mangled_function_name:'.
    if grep -q 'class StatsCollector' "$MUTMUT_MAIN" && \
       ! grep -q 'if function in mutmut.tests_by_mangled_function_name:' "$MUTMUT_MAIN"; then
        sed -i '/for function in mutmut._stats:/{
            n
            s|                    mutmut.tests_by_mangled_function_name\[function\].add(|                    if function in mutmut.tests_by_mangled_function_name:\n                        mutmut.tests_by_mangled_function_name[function].add(|
        }' "$MUTMUT_MAIN"
        PATCHED=$((PATCHED + 1))
        echo "  Patch 2 applied: KeyError guard in StatsCollector ✓"
    else
        echo "  Patch 2 already applied ✓"
    fi

    # Patch 3: Hardcoded test file fallbacks in PytestRunner.
    # run_stats() and run_tests() fall back to specific test files when no tests
    # are provided. Replace with 'tests/' so all tests are discovered.
    if grep -q "test_query_handler.py\|test_real_features.py\|test_vector_retrieval.py\|test_retriever.py" "$MUTMUT_MAIN"; then
        sed -i "s|\['tests/test_query_handler.py', 'tests/test_real_features.py'\]|['tests/']|g" "$MUTMUT_MAIN"
        sed -i "s|\['tests/test_vector_retrieval.py', 'tests/test_retriever.py'\]|['tests/']|g" "$MUTMUT_MAIN"
        PATCHED=$((PATCHED + 1))
        echo "  Patch 3 applied: hardcoded test paths → tests/ ✓"
    else
        echo "  Patch 3 already applied ✓"
    fi

    echo "mutmut patches verified ($PATCHED new patches applied) ✓"
else
    echo "WARNING: mutmut __main__.py not found — patches will be applied after mutmut install"
fi

# --- Step 7: Database migrations ---
echo ""
echo "--- Step 7: Checking Alembic migrations ---"
if [ -f "alembic.ini" ]; then
    echo "Alembic config found ✓ (run 'alembic upgrade head' when database is available)"
else
    echo "No alembic.ini found (will be created during feature implementation)"
fi

# --- Step 8: Create .env from example if missing ---
echo ""
echo "--- Step 8: Checking .env ---"
if [ -f ".env" ]; then
    echo ".env file exists ✓"
elif [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created .env from .env.example — please fill in the values"
else
    echo "No .env or .env.example found (will be created during initialization)"
fi

# --- Step 9: Verify ---
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

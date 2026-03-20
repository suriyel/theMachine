$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Code Context Retrieval — Environment Bootstrap ==="

# --- Step 1: Python version check ---
$RequiredPython = "3.11"
Write-Host ""
Write-Host "--- Step 1: Checking Python version ---"

$PythonCmd = $null
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} else {
    Write-Host "ERROR: Python not found. Please install Python >= $RequiredPython"
    exit 1
}

$PythonVersion = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$PythonMajor = & $PythonCmd -c "import sys; print(sys.version_info.major)"
$PythonMinor = & $PythonCmd -c "import sys; print(sys.version_info.minor)"

if ([int]$PythonMajor -lt 3 -or ([int]$PythonMajor -eq 3 -and [int]$PythonMinor -lt 11)) {
    Write-Host "ERROR: Python >= $RequiredPython required, found $PythonVersion"
    exit 1
}
Write-Host "Found Python $PythonVersion"

# --- Step 2: Virtual environment creation ---
Write-Host ""
Write-Host "--- Step 2: Creating virtual environment ---"

if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists at .venv"
} else {
    & $PythonCmd -m venv .venv
    Write-Host "Created virtual environment at .venv"
}

# --- Step 3: Activate environment ---
Write-Host ""
Write-Host "--- Step 3: Activating environment ---"
& .\.venv\Scripts\Activate.ps1
Write-Host "Activated .venv"

# --- Step 4: Install dependencies ---
Write-Host ""
Write-Host "--- Step 4: Installing dependencies ---"

pip install --upgrade pip setuptools wheel --quiet

# Install PyTorch CPU-only
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu --quiet

if (Test-Path "pyproject.toml") {
    pip install -e ".[dev]" --quiet
    Write-Host "Installed project with dev dependencies"
} elseif (Test-Path "requirements.txt") {
    pip install -r requirements.txt --quiet
    if (Test-Path "requirements-dev.txt") {
        pip install -r requirements-dev.txt --quiet
    }
    Write-Host "Installed requirements"
} else {
    Write-Host "WARNING: No pyproject.toml or requirements.txt found"
}

# --- Step 5: Dev tools ---
Write-Host ""
Write-Host "--- Step 5: Verifying dev tools ---"
pip install pytest pytest-cov pytest-asyncio mutmut --quiet
Write-Host "Dev tools installed"

# --- Step 6: .env setup ---
Write-Host ""
Write-Host "--- Step 6: Checking .env ---"
if (Test-Path ".env") {
    Write-Host ".env file exists"
} elseif (Test-Path ".env.example") {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example — please fill in the values"
}

# --- Step 7: Verify ---
Write-Host ""
Write-Host "=== Environment Check ==="
Write-Host "Python:  $(python --version)"
Write-Host "pytest:  $(pytest --version 2>&1 | Select-Object -First 1)"
Write-Host ""
Write-Host "=== Environment ready. ==="
Write-Host ""
Write-Host "To activate: .\.venv\Scripts\Activate.ps1"
Write-Host "To run tests: pytest --cov=src --cov-branch --cov-report=term-missing tests/"

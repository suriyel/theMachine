$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$VenvDir = ".venv"

Write-Host "=== Code Context Retrieval — Environment Bootstrap ===" -ForegroundColor Cyan

# --- Step 1: Detect Python ---
$PythonBin = $null
foreach ($candidate in @("python3.11", "python3", "python")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $PythonBin = $candidate
        break
    }
}
if (-not $PythonBin) {
    Write-Error "Python not found. Install Python >= 3.11 from https://www.python.org/downloads/"
    exit 1
}

# Version check
$VersionOutput = & $PythonBin --version 2>&1
Write-Host "Found $VersionOutput at $(Get-Command $PythonBin | Select-Object -ExpandProperty Source)"

# --- Step 2: Create virtual environment ---
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $PythonBin -m venv $VenvDir
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# --- Step 3: Activate environment ---
& "$VenvDir\Scripts\Activate.ps1"

# --- Step 4: Upgrade pip ---
Write-Host "Upgrading pip..." -ForegroundColor Yellow
pip install --upgrade pip --quiet

# --- Step 5: Install dependencies ---
if (Test-Path "requirements.txt") {
    Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt --quiet
}

if (Test-Path "requirements-dev.txt") {
    Write-Host "Installing dev dependencies from requirements-dev.txt..." -ForegroundColor Yellow
    pip install -r requirements-dev.txt --quiet
}

# --- Step 6: Install dev tools ---
Write-Host "Installing development tools..." -ForegroundColor Yellow
pip install pytest pytest-cov mutmut --quiet

# --- Step 7: Verify ---
Write-Host ""
Write-Host "=== Environment Check ===" -ForegroundColor Cyan
Write-Host "python:   $(python --version)"
Write-Host "pip:      $(pip --version)".Split()[0..1] -join " "
Write-Host "pytest:   $(pytest --version 2>&1 | Select-Object -First 1)"
$coverageVersion = python -c "import coverage; print(coverage.__version__)" 2>$null
if ($coverageVersion) {
    Write-Host "coverage: coverage $coverageVersion"
} else {
    Write-Host "coverage: not installed"
}
Write-Host ""
Write-Host "Environment ready." -ForegroundColor Green
Write-Host "Run: & $VenvDir\Scripts\Activate.ps1"

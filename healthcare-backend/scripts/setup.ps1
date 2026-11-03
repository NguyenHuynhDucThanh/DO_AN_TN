param([string]$PythonPath = "")

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $backendRoot
try {
    if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
        if ($PythonPath) {
            & $PythonPath -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 required'"
            if ($LASTEXITCODE -ne 0) { throw "Python 3.12 is required." }
            & $PythonPath -m venv .venv
        } else {
            & py -3.12 -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) { throw "Cannot create venv. Use -PythonPath with the full Python 3.12 path." }
    }
    & .\.venv\Scripts\python.exe -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 required'"
    if ($LASTEXITCODE -ne 0) { throw "Existing venv is not Python 3.12. Keep it for review; create a correct environment manually." }
    if (Test-Path -LiteralPath "requirements.lock.txt") {
        & .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
    } else {
        & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    }
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    if (-not (Test-Path -LiteralPath ".env")) { Copy-Item -LiteralPath ".env.example" -Destination ".env" }
    Write-Host "Backend ready. Run .venv\Scripts\python.exe scripts\bootstrap_database.py next."
} finally {
    Pop-Location
}

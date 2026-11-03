# Interactive local setup. The administrator password is entered privately by the user.
param([switch]$KeepOpen)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
$resultPath = Join-Path $backendRoot "data\database-setup-result.json"
$result = @{ status = "failed"; completed_at = $null }
Push-Location $backendRoot
try {
    Write-Host "Initialize the healthcare development database."
    Write-Host "Enter your PostgreSQL postgres password at the hidden prompt. It is not sent to chat or saved."
    & .\.venv\Scripts\python.exe .\scripts\bootstrap_database.py
    if ($LASTEXITCODE -ne 0) { throw "Database bootstrap failed. See the message above; existing credentials were not reset." }
    & .\.venv\Scripts\python.exe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed." }
    & .\.venv\Scripts\python.exe .\scripts\check_database.py
    if ($LASTEXITCODE -ne 0) { throw "Database verification failed." }
    $result.status = "ready"
    Write-Host "Database, pgvector and Alembic are ready. You can close this window."
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
} finally {
    $result.completed_at = [DateTime]::UtcNow.ToString("o")
    $result | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
    Pop-Location
    if ($KeepOpen) { Read-Host "Press Enter to close" | Out-Null }
}
if ($result.status -ne "ready") { exit 1 }

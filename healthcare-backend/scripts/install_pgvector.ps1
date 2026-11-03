param(
    [string]$PostgresRoot = "C:\Program Files\PostgreSQL\18",
    [ValidatePattern('^v\d+\.\d+\.\d+$')]
    [string]$Version = "v0.8.7"
)

$ErrorActionPreference = "Stop"
$installLog = Join-Path (Split-Path -Parent $PSScriptRoot) "data\pgvector-install.log"
Start-Transcript -Path $installLog -Append | Out-Null
try {
$administrator = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $administrator) {
    throw "Open PowerShell as Administrator to install pgvector into PostgreSQL. This script does not change database passwords or pg_hba.conf."
}
if (-not [Environment]::Is64BitProcess) { throw "Run 64-bit PowerShell for PostgreSQL x64." }

$pgConfig = Join-Path $PostgresRoot "bin\pg_config.exe"
$postgresExe = Join-Path $PostgresRoot "bin\postgres.exe"
if (-not (Test-Path -LiteralPath $pgConfig)) { throw "pg_config.exe not found. Set -PostgresRoot to the PostgreSQL server directory." }
$postgresVersion = & $pgConfig --version
if ($LASTEXITCODE -ne 0 -or $postgresVersion -notmatch '^PostgreSQL (\d+)\.') { throw "Cannot determine PostgreSQL version." }
if ([int]$Matches[1] -lt 13) { throw "This pgvector release requires PostgreSQL 13 or newer." }

$reader = [IO.BinaryReader]::new([IO.File]::OpenRead($postgresExe))
try {
    $reader.BaseStream.Position = 0x3c
    $peOffset = $reader.ReadInt32()
    $reader.BaseStream.Position = $peOffset + 4
    if ($reader.ReadUInt16() -ne 0x8664) { throw "PostgreSQL server must be x64; do not install a DLL built for another architecture." }
} finally { $reader.Dispose() }

$extensionDir = Join-Path (& $pgConfig --sharedir) "extension"
if (Test-Path -LiteralPath (Join-Path $extensionDir "vector.control")) {
    Write-Host "pgvector server files already exist. Keep them; run bootstrap_database.py to enable/verify the extension."
    return
}

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$visualStudio = if (Test-Path -LiteralPath $vswhere) {
    & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
}
if (-not $visualStudio) {
    throw @"
Microsoft C++ x64 Build Tools are missing. Install them, then run this script again:
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
Select Desktop development with C++ / MSVC x64 and a Windows SDK if using the installer UI.
Official instructions: https://github.com/pgvector/pgvector#windows
"@
}

$devCommand = Join-Path $visualStudio "Common7\Tools\VsDevCmd.bat"
if (-not (Test-Path -LiteralPath $devCommand)) { throw "Visual Studio native tool environment is missing." }
$buildRoot = Join-Path ([IO.Path]::GetTempPath()) ("healthcare-pgvector-" + [guid]::NewGuid().ToString("N"))
& git clone --depth 1 --branch $Version https://github.com/pgvector/pgvector.git $buildRoot
if ($LASTEXITCODE -ne 0) { throw "Cannot download official pgvector source." }

$previousPgRoot = $env:PGROOT
Push-Location $buildRoot
try {
    $env:PGROOT = $PostgresRoot
    # Both build and installation use Microsoft's x64 native tools and the same PGROOT.
    $buildCommand = 'call "{0}" -arch=x64 -host_arch=x64 && nmake /F Makefile.win && nmake /F Makefile.win install' -f $devCommand
    & cmd.exe /d /c $buildCommand
    if ($LASTEXITCODE -ne 0) { throw "pgvector build/install failed. Inspect compiler output; keep the source directory for diagnosis: $buildRoot" }
} finally {
    $env:PGROOT = $previousPgRoot
    Pop-Location
}

if (-not (Test-Path -LiteralPath (Join-Path $extensionDir "vector.control"))) { throw "Build completed but vector.control is missing from the target server." }
Write-Host "Installed pgvector $Version for $postgresVersion x64. Source retained at $buildRoot."
Write-Host "Next: run bootstrap_database.py in a normal terminal and enter your PostgreSQL password privately."
} finally {
    Stop-Transcript | Out-Null
}

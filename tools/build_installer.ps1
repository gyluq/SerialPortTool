# Build the executable and wrap it into a Windows installer.
#
#   powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1
#
# Steps: run the test suite, build the onefile exe, compile the Inno Setup
# script. Pass -SkipTests to go straight to packaging, or -Python <path> if the
# interpreter with PySide6 is not the first one on PATH.

param(
    [string]$Python = "",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# A bare `python` on PATH is not necessarily the one with the runtime
# dependencies installed, so probe each candidate instead of assuming.
if (-not $Python) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
    )
    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath) { $candidates += $onPath.Source }

    foreach ($candidate in $candidates) {
        if (-not (Test-Path $candidate)) { continue }
        & $candidate -c "import PySide6, serial" 2>$null
        if ($LASTEXITCODE -eq 0) { $Python = $candidate; break }
    }
}

if (-not $Python -or -not (Test-Path $Python)) {
    throw "No Python with PySide6 and pyserial found. Pass -Python <path>."
}
Write-Host "Python: $Python"

if (-not $SkipTests) {
    Write-Host "==> Running tests"
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; refusing to package a broken build." }
}

Write-Host "==> Building executable"
& $Python -m PyInstaller packaging.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

$exe = Join-Path $root "dist\SerialPortTool.exe"
if (-not (Test-Path $exe)) { throw "Expected output missing: $exe" }
Write-Host ("    dist\SerialPortTool.exe ({0:N1} MB)" -f ((Get-Item $exe).Length / 1MB))

# Note: "$env:ProgramFiles(x86)" does not parse reliably inside a string, so
# resolve the variable first and combine with Join-Path.
$programFilesX86 = ${env:ProgramFiles(x86)}
if (-not $programFilesX86) { $programFilesX86 = $env:ProgramFiles }

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
$isccPath = if ($iscc) { $iscc.Source } else {
    @(
        (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $isccPath) {
    Write-Warning "Inno Setup 6 not found. The executable is ready at dist\SerialPortTool.exe."
    Write-Warning "Install it and re-run:"
    Write-Warning "    winget install --id JRSoftware.InnoSetup -e"
    exit 0
}

Write-Host "==> Compiling installer"
& $isccPath "installer\SerialPortTool.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

$setup = Get-ChildItem "dist\*-setup.exe" | Sort-Object LastWriteTime | Select-Object -Last 1
Write-Host ""
Write-Host ("Installer ready: dist\{0} ({1:N1} MB)" -f $setup.Name, ($setup.Length / 1MB))

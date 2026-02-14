$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv-build"
$Python = $env:PYTHON
if (-not $Python) { $Python = "python" }

# Use optimized spec by default, fallback to original
$UseOptimized = $true
if ($env:USE_LEGACY_BUILD -eq "1") { $UseOptimized = $false }

Write-Host "=== BPM Detector Pro - Windows Build ===" -ForegroundColor Cyan
if ($UseOptimized) {
  Write-Host "Mode: OPTIMIZED (fast startup, small size)" -ForegroundColor Green
} else {
  Write-Host "Mode: Legacy (full librosa)" -ForegroundColor Yellow
}

# ONEDIR mode: DLLs are normal files on disk, no dynamic extraction.
# This is the ONLY way to reliably avoid "Failed to load Python DLL" errors
# caused by Windows Defender blocking memory-mapped DLL loading.
Write-Host "Layout: ONEDIR (folder with pre-extracted DLLs, distributed as ZIP)" -ForegroundColor Green

if (-not (Test-Path $Venv)) {
  Write-Host "Creating virtual environment..."
  & $Python -m venv $Venv
}

$PyExe = Join-Path $Venv "Scripts\python.exe"
$PyInstaller = Join-Path $Venv "Scripts\pyinstaller.exe"

Write-Host "Sync version from git tag..."
$UpdateScript = Join-Path $Root "scripts\\update_version.py"
if (Test-Path $UpdateScript) {
  & $PyExe $UpdateScript
} else {
  Write-Warning "update_version.py not found; using existing app_version.py"
}

Write-Host "Installing dependencies..."
& $PyExe -m pip install --upgrade pip --quiet

if ($UseOptimized) {
  Write-Host "Using minimal requirements for optimized build..."
  if (Test-Path (Join-Path $Root "requirements-minimal.txt")) {
    & $PyExe -m pip install -r (Join-Path $Root "requirements-minimal.txt") pyinstaller --quiet
  } else {
    Write-Warning "requirements-minimal.txt not found, using full requirements.txt"
    & $PyExe -m pip install -r (Join-Path $Root "requirements.txt") pyinstaller --quiet
  }
} else {
    & $PyExe -m pip install -r (Join-Path $Root "requirements.txt") pyinstaller --quiet
}

# Check for FFmpeg
$Ffmpeg = $env:FFMPEG_BINARY
if (-not $Ffmpeg) {
  $Candidate = Join-Path $Root "packaging\ffmpeg\windows\ffmpeg.exe"
  if (Test-Path $Candidate) { $Ffmpeg = $Candidate }
}

if (-not $Ffmpeg) {
  Write-Error "ffmpeg introuvable. Place-le dans packaging\\ffmpeg\\windows\\ffmpeg.exe ou definis FFMPEG_BINARY."
  exit 1
}

Write-Host "FFmpeg found: $Ffmpeg"

# UPX is optional (can increase SmartScreen/Defender heuristic flags)
$UseUpx = $env:USE_UPX -eq "1"
$UpxDir = Join-Path $Root "tools\upx"
$UpxExe = Join-Path $UpxDir "upx.exe"

if ($UseUpx) {
  if (-not (Test-Path $UpxExe)) {
    Write-Host "Downloading UPX for better compression..."
    try {
      $UpxUrl = "https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-win64.zip"
      $UpxZip = Join-Path $env:TEMP "upx.zip"
      Invoke-WebRequest -Uri $UpxUrl -OutFile $UpxZip -UseBasicParsing
      New-Item -ItemType Directory -Path $UpxDir -Force | Out-Null
      Expand-Archive -Path $UpxZip -DestinationPath $env:TEMP -Force
      Copy-Item (Join-Path $env:TEMP "upx-4.2.2-win64\upx.exe") $UpxDir
      Remove-Item $UpxZip -Force
      Write-Host "UPX installed successfully" -ForegroundColor Green
    } catch {
      Write-Host "UPX download failed, continuing without compression..." -ForegroundColor Yellow
      $UseUpx = $false
    }
  }
} else {
  Write-Host "UPX disabled (set USE_UPX=1 to enable compression)" -ForegroundColor Yellow
}

# Select spec file
if ($UseOptimized) {
  $SpecFile = Join-Path $Root "bpm-detector-optimized.spec"
  if (-not (Test-Path $SpecFile)) {
    Write-Host "Optimized spec not found, using legacy..." -ForegroundColor Yellow
    $SpecFile = Join-Path $Root "bpm-detector.spec"
  }
} else {
  $SpecFile = Join-Path $Root "bpm-detector.spec"
}

Write-Host "Building with: $SpecFile"

# Build with UPX if available and enabled
$UpxArgs = @()
if ($UseUpx -and (Test-Path $UpxExe)) {
  $UpxArgs = @("--upx-dir", $UpxDir)
  Write-Host "Using UPX compression from: $UpxDir" -ForegroundColor Green
}

& $PyInstaller --noconfirm --clean @UpxArgs $SpecFile

# Onedir produces a folder, create ZIP for distribution
$OutputDir = Join-Path $Root "dist\BPM-Detector-Pro"
$OutputExe = Join-Path $OutputDir "BPM-Detector-Pro.exe"
$OutputZip = Join-Path $Root "dist\BPM-Detector-Pro-Windows-x64.zip"

if (Test-Path $OutputExe) {
  # Remove old ZIP if it exists
  if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
  
  # Create ZIP from the onedir folder
  Write-Host "Creating ZIP archive..."
  Compress-Archive -Path $OutputDir -DestinationPath $OutputZip -CompressionLevel Optimal
  
  $ExeSize = (Get-Item $OutputExe).Length / 1MB
  $ZipSize = (Get-Item $OutputZip).Length / 1MB
  $FileCount = (Get-ChildItem -Recurse $OutputDir | Measure-Object).Count
  Write-Host ""
  Write-Host "=== BUILD SUCCESS ===" -ForegroundColor Green
  Write-Host "Output folder: $OutputDir ($FileCount files)"
  Write-Host ("EXE size: {0:N1} MB" -f $ExeSize)
  Write-Host ("ZIP size: {0:N1} MB" -f $ZipSize)
  Write-Host "ZIP: $OutputZip"
} else {
  Write-Error "Build failed - output not found at $OutputExe"
  exit 1
}

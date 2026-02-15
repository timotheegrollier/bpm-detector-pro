$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv-build"
$Python = $env:PYTHON
if (-not $Python) { $Python = "python" }

Write-Host "=== BPM-detector - Windows Build ===" -ForegroundColor Cyan
Write-Host "Mode: Standard (optimized runtime profile)" -ForegroundColor Green

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

Write-Host "Installing runtime dependencies..."
if (Test-Path (Join-Path $Root "requirements-minimal.txt")) {
  & $PyExe -m pip install -r (Join-Path $Root "requirements-minimal.txt") pyinstaller --quiet
} else {
  Write-Warning "requirements-minimal.txt not found, using requirements.txt"
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

# Single packaging profile
$SpecFile = Join-Path $Root "bpm-detector.spec"

Write-Host "Building with: $SpecFile"

# Build with UPX if available and enabled
$UpxArgs = @()
if ($UseUpx -and (Test-Path $UpxExe)) {
  $UpxArgs = @("--upx-dir", $UpxDir)
  Write-Host "Using UPX compression from: $UpxDir" -ForegroundColor Green
}

& $PyInstaller --noconfirm --clean @UpxArgs $SpecFile

# Onedir produces a folder, create ZIP for distribution
$OutputDir = Join-Path $Root "dist\BPM-detector"
$OutputExe = Join-Path $OutputDir "BPM-detector.exe"
$OutputZip = Join-Path $Root "dist\BPM-detector-Windows-x64.zip"
$InternalDir = Join-Path $OutputDir "_internal"

# Collect required runtime DLL names from the build Python version.
$PythonDllName = (& $PyExe -c "import sys; print(f'python{sys.version_info.major}{sys.version_info.minor}.dll')").Trim()
$RequiredInternalDlls = @(
  $PythonDllName
  "vcruntime140.dll"
  "vcruntime140_1.dll"
)
$OptionalInternalDlls = @("msvcp140.dll")

function Find-SystemDllPath {
  param(
    [string]$DllName,
    [string]$PythonExePath
  )

  $PythonDir = Split-Path -Parent $PythonExePath
  $SystemRoot = $env:SystemRoot
  $CandidateDirs = @(
    $PythonDir
    (Join-Path $PythonDir "..")
    (Join-Path $SystemRoot "System32")
    (Join-Path $SystemRoot "SysWOW64")
  )

  if ($env:PATH) {
    $CandidateDirs += ($env:PATH -split ";" | Where-Object { $_ -and $_.Trim() })
  }

  $Seen = @{}
  foreach ($Dir in $CandidateDirs) {
    if (-not $Dir) { continue }
    $FullDir = [System.IO.Path]::GetFullPath($Dir)
    if ($Seen.ContainsKey($FullDir)) { continue }
    $Seen[$FullDir] = $true
    $Candidate = Join-Path $FullDir $DllName
    if (Test-Path $Candidate) {
      return $Candidate
    }
  }

  # Last resort: scan common VC++ Redist install roots.
  $RedistRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ -and (Test-Path $_) }
  foreach ($RootDir in $RedistRoots) {
    $Match = Get-ChildItem -Path $RootDir -Recurse -Filter $DllName -File -ErrorAction SilentlyContinue |
      Select-Object -First 1
    if ($Match) {
      return $Match.FullName
    }
  }

  return $null
}

if (Test-Path $OutputExe) {
  if (-not (Test-Path $InternalDir)) {
    Write-Error "Build invalid: missing internal directory $InternalDir"
    exit 1
  }

  foreach ($DllName in ($RequiredInternalDlls + $OptionalInternalDlls)) {
    $DllPath = Join-Path $InternalDir $DllName
    if (Test-Path $DllPath) { continue }
    $FallbackPath = Find-SystemDllPath -DllName $DllName -PythonExePath $PyExe
    if ($FallbackPath) {
      Copy-Item $FallbackPath $DllPath -Force
      Write-Host "Added runtime DLL fallback: $DllName from $FallbackPath"
    }
  }

  $MissingRequiredDlls = @()
  foreach ($DllName in $RequiredInternalDlls) {
    if (-not (Test-Path (Join-Path $InternalDir $DllName))) {
      $MissingRequiredDlls += $DllName
    }
  }

  if ($MissingRequiredDlls.Count -gt 0) {
    Write-Error ("Build invalid: missing required runtime DLL(s) in _internal: " + ($MissingRequiredDlls -join ", "))
    exit 1
  }

  $MissingOptionalDlls = @()
  foreach ($DllName in $OptionalInternalDlls) {
    if (-not (Test-Path (Join-Path $InternalDir $DllName))) {
      $MissingOptionalDlls += $DllName
    }
  }
  if ($MissingOptionalDlls.Count -gt 0) {
    Write-Warning ("Optional runtime DLL(s) not bundled: " + ($MissingOptionalDlls -join ", ") + ". System VC++ Redistributable may be required.")
  }

  $ReadmePath = Join-Path $OutputDir "README-Windows.txt"
  @'
BPM-detector - Windows x64
==============================

IMPORTANT:
- This package is for Windows 11/10 x64 only.
- Keep BPM-detector.exe and the _internal folder together.
- Do not move BPM-detector.exe alone outside this folder.

Recommended start:
- Double-click BPM-detector.exe

If you get "Failed to load Python DLL":
1) Right-click the ZIP file > Properties > check "Unblock", then extract again.
2) Extract to a short local path (example: C:\BPM-detector\).
3) Install/repair Microsoft Visual C++ Redistributable 2015-2022 (x64).
'@ | Set-Content -Path $ReadmePath -Encoding ascii

  # Remove old ZIP if it exists
  if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
  
  # Create ZIP from the onedir folder.
  # Prefer 7-Zip when available for smaller archives; fallback to Compress-Archive.
  Write-Host "Creating ZIP archive..."
  $SevenZipCmd = Get-Command 7z -ErrorAction SilentlyContinue
  if (-not $SevenZipCmd) {
    $SevenZipCmd = Get-Command 7z.exe -ErrorAction SilentlyContinue
  }
  if ($SevenZipCmd) {
    & $SevenZipCmd.Source a -tzip -mx=9 -mfb=258 -mpass=15 -y $OutputZip $OutputDir | Out-Null
  } else {
    Compress-Archive -Path $OutputDir -DestinationPath $OutputZip -CompressionLevel Optimal -Force
  }
  
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

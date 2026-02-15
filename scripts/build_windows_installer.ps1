$ErrorActionPreference = "Stop"

[CmdletBinding()]
param(
  [string]$InputDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "dist\BPM-detector"),
  [string]$OutputDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "dist"),
  [string]$Version = ""
)

function Resolve-Iscc {
  $Cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
  if ($Cmd) { return $Cmd.Source }

  $Candidates = @()
  if (${env:ProgramFiles(x86)}) {
    $Candidates += (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
  }
  if ($env:ProgramFiles) {
    $Candidates += (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
  }

  foreach ($Candidate in $Candidates) {
    if ($Candidate -and (Test-Path $Candidate)) {
      return $Candidate
    }
  }

  throw "ISCC.exe not found. Install Inno Setup 6."
}

function Get-AppVersionFromFile {
  param([string]$VersionFilePath)

  if (-not (Test-Path $VersionFilePath)) { return $null }
  $Raw = Get-Content $VersionFilePath -Raw
  $Match = [Regex]::Match($Raw, 'APP_VERSION\s*=\s*"([^"]+)"')
  if ($Match.Success) {
    return $Match.Groups[1].Value
  }
  return $null
}

$Root = Split-Path -Parent $PSScriptRoot
$IssFile = Join-Path $Root "packaging\windows\BPM-detector.iss"
$OutputName = "BPM-detector-Setup-Windows-x64.exe"

if (-not (Test-Path $InputDir)) {
  throw "Input directory not found: $InputDir"
}
if (-not (Test-Path (Join-Path $InputDir "BPM-detector.exe"))) {
  throw "Main executable missing in input directory: $InputDir\BPM-detector.exe"
}
if (-not (Test-Path $IssFile)) {
  throw "Inno Setup script not found: $IssFile"
}

if (-not $Version) {
  $Version = Get-AppVersionFromFile -VersionFilePath (Join-Path $Root "app_version.py")
}
if (-not $Version) {
  $Version = "0.0.0"
  Write-Warning "Version not found in app_version.py. Using $Version."
}

$Iscc = Resolve-Iscc
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

Write-Host "=== BPM-detector - Windows Installer Build ===" -ForegroundColor Cyan
Write-Host "ISCC: $Iscc"
Write-Host "InputDir: $InputDir"
Write-Host "OutputDir: $OutputDir"
Write-Host "Version: $Version"

$Args = @(
  "/DAppVersion=$Version",
  "/DSourceDir=$InputDir",
  "/DOutputDir=$OutputDir",
  $IssFile
)

& $Iscc @Args
if ($LASTEXITCODE -ne 0) {
  throw "ISCC failed with exit code $LASTEXITCODE."
}

$OutputInstaller = Join-Path $OutputDir $OutputName
if (-not (Test-Path $OutputInstaller)) {
  throw "Installer was not generated: $OutputInstaller"
}

$SizeMb = (Get-Item $OutputInstaller).Length / 1MB
Write-Host ("Installer OK: {0} ({1:N1} MB)" -f $OutputInstaller, $SizeMb) -ForegroundColor Green

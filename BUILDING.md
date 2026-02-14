# Build Guide - BPM Detector Pro

This project uses PyInstaller to generate standalone desktop binaries.

## Recommended Build Path

Use the optimized build pipeline by default. It delivers smaller artifacts and faster startup.

### Windows (optimized)

```powershell
.\scripts\build_windows.ps1
```

Outputs:

- `dist\BPM-Detector-Pro\` (ONEDIR folder)
- `dist\BPM-Detector-Pro-Windows-x64.zip` (release archive)

Notes:

- Windows build uses ONEDIR by default to reduce DLL startup/runtime issues.
- A release ZIP is generated automatically.
- The script syncs app version from the latest Git tag (example: `v1.3.1`).
- You can override the version: `set APP_VERSION=1.3.1` before running the build.

### Linux (optimized)

```bash
./scripts/build_linux.sh
```

Output:

- `dist/BPM-Detector-Pro`

The Linux script also syncs version from the latest Git tag.

## Classic Build (full librosa profile)

If you need the non-optimized/full profile:

### Windows

```powershell
$env:USE_LEGACY_BUILD = "1"
.\scripts\build_windows.ps1
```

### Linux

```bash
pyinstaller bpm-detector.spec --clean
```

## Prerequisites

1. FFmpeg binary in expected location:

- Windows: `packaging/ffmpeg/windows/ffmpeg.exe`
- Linux: `packaging/ffmpeg/linux/ffmpeg`
- macOS: `packaging/ffmpeg/macos/ffmpeg` (if building macOS)

2. Python dependencies:

```bash
# Minimal/optimized profile
pip install -r requirements-minimal.txt pyinstaller

# Full profile
pip install -r requirements.txt pyinstaller
```

## Applied Optimizations

| Optimization | Impact |
|---|---|
| Lazy-loading heavy libraries | Faster cold startup |
| Aggressive optional-module exclusion | Smaller bundles |
| Limited default analysis window | Lower CPU cost |
| ONEDIR default on Windows | Better runtime reliability |

## Troubleshooting

### "FFmpeg not found"

- Download FFmpeg from https://ffmpeg.org/download.html
- Put the binary in the expected path above
- Or set `FFMPEG_BINARY` / `FFMPEG_PATH` to a valid executable path

### Windows SmartScreen / Defender warnings

- Unsigned executables can trigger warnings.
- Keep ONEDIR packaging and avoid moving only the `.exe` file.
- Sign the executable (Authenticode) for production distribution.

### App starts slowly on Windows

- Antivirus may scan executable/runtime DLLs on first launch.
- Add an exclusion for the extracted app folder if needed.
- Subsequent launches are typically faster.

### "python311.dll" or "python3.dll" missing

- Extract the full ZIP folder.
- Launch `START-BPM-Detector-Pro.cmd`.
- If needed, install/repair `Microsoft Visual C++ Redistributable 2015-2022 (x64)`.

## Release CI

GitHub Actions release workflow runs on pushed tags matching `v*`.

Example:

```bash
git tag v1.3.1
git push origin master --tags
```

That tag push builds Linux/Windows/macOS artifacts and publishes the release.

# Build Guide - BPM-detector

This project uses PyInstaller to generate standalone desktop binaries.

## Build Profile

The project now ships a single desktop runtime profile across platforms.
There is no separate legacy/full packaging mode.

### Windows

```powershell
.\scripts\build_windows.ps1
```

Outputs:

- `dist\BPM-detector\` (ONEDIR folder)
- `dist\BPM-detector-Windows-x64.zip` (release archive)

To generate an installer (`Setup.exe`) after the ONEDIR build:

```powershell
.\scripts\build_windows_installer.ps1
```

Additional output:

- `dist\BPM-detector-Setup-Windows-x64.exe` (installer with Start Menu shortcut + optional desktop shortcut)

Notes:

- Windows build uses ONEDIR by default to reduce DLL startup/runtime issues.
- A release ZIP is generated automatically.
- The script syncs app version from the latest Git tag (example: `v1.3.2`).
- You can override the version: `set APP_VERSION=1.3.2` before running the build.

### Linux

```bash
./scripts/build_linux.sh
```

Output:

- `dist/BPM-detector`

The Linux script also syncs version from the latest Git tag.

## Prerequisites

1. FFmpeg binary in expected location:

- Windows: `packaging/ffmpeg/windows/ffmpeg.exe`
- Linux: `packaging/ffmpeg/linux/ffmpeg`
- macOS: `packaging/ffmpeg/macos/ffmpeg` (if building macOS)

2. Python dependencies:

```bash
# Packaging profile
pip install -r requirements-minimal.txt pyinstaller
```

3. Inno Setup 6 (Windows installer generation):

- Install Inno Setup from https://jrsoftware.org/isinfo.php
- Ensure `ISCC.exe` is available (default install path is supported by the script)

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
- A Setup installer improves installation UX (shortcuts, fixed install path), but does not guarantee SmartScreen trust by itself.

### App starts slowly on Windows

- Antivirus may scan executable/runtime DLLs on first launch.
- Add an exclusion for the extracted app folder if needed.
- Subsequent launches are typically faster.

### "python311.dll" or "python3.dll" missing

- Extract the full ZIP folder.
- Launch `BPM-detector.exe` directly from the extracted folder.
- If needed, install/repair `Microsoft Visual C++ Redistributable 2015-2022 (x64)`.

## Checksums

Generate SHA256 hashes for a release directory:

```bash
python scripts/generate_checksums.py release --output release/checksums.txt --relative-to release
```

Verify:

```bash
sha256sum -c release/checksums.txt
```

## Release CI

GitHub Actions release workflow runs on pushed tags matching `v*`.
Windows CI now publishes both:

- `BPM-detector-Windows-x64.zip` (portable ONEDIR)
- `BPM-detector-Setup-Windows-x64.exe` (installer)
- `checksums.txt` (SHA256 hashes for all release files)

Example:

```bash
git tag v1.3.2
git push origin master --tags
```

That tag push builds Linux/Windows/macOS artifacts and publishes the release.

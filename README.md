# BPM-detector

High-precision BPM detection for audio files with a modern desktop GUI and CLI.

![Version](https://img.shields.io/badge/version-1.4.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)

## Features

- High-precision BPM detection (hybrid autocorrelation + beat analysis)
- Fast desktop GUI startup
- Multi-file batch selection from the GUI (`Fichiers...` supports Ctrl/Cmd+click)
- Folder analysis mode for large-library scans
- CLI mode for automation and scripting
- Portable binaries with bundled FFmpeg (no system FFmpeg required in release artifacts)
- Supports common formats: MP3, FLAC, WAV, M4A, OGG, AAC, and more

## Quick Start

### Option 1: Portable Binaries (Recommended)

Download artifacts from [GitHub Releases](../../releases):

- Linux: `BPM-detector-Linux-x64`
- Windows: `BPM-detector-Windows-x64.zip`
- Windows Installer: `BPM-detector-Setup-Windows-x64.exe`
- macOS: `BPM-detector-macOS.dmg`
- Checksums: `checksums.txt`

Windows note:

- Extract the full ZIP folder before launching.
- Start `BPM-detector.exe` directly (no `.cmd` launcher required).
- Do not move only the `.exe` without the `_internal` directory.
- Installer mode is available if you prefer Start Menu/Desktop shortcuts.

### Option 2: Run from Source

```bash
git clone https://github.com/timotheegrollier/bpm-detector.git
cd bpm-detector

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

If running from source, make sure FFmpeg is installed or available through `FFMPEG_BINARY` / `FFMPEG_PATH`.

### Verify Download Integrity

Use the `checksums.txt` file from the same release:

```bash
sha256sum -c checksums.txt
```

On Windows PowerShell:

```powershell
Get-FileHash .\BPM-detector-Setup-Windows-x64.exe -Algorithm SHA256
```

Compare the resulting hash with the corresponding entry in `checksums.txt`.

## Usage

### Desktop GUI

```bash
python bpm_gui.py
# or use packaged binary
# note: bpm_gui_fast.py is only a compatibility alias to bpm_gui.py
```

GUI workflow:

- `Fichiers...`: pick one or many files (Ctrl/Cmd+click)
- `Dossier...`: analyze all supported audio files in one folder
- `LANCER L'ANALYSE`: run batch analysis and monitor progress

### CLI

```bash
python bpm_detect.py track.mp3
```

Common options:

| Option | Description | Default |
|---|---|---|
| `--start N` | Analysis start offset (seconds) | `0` |
| `--duration N` | Analysis duration (seconds) | Full file |
| `--sr N` | Analysis sample rate | `22050` |
| `--hop-length N` | Time precision (smaller = more precise, slower) | `96` |
| `--min-bpm N` | Minimum BPM | `60` |
| `--max-bpm N` | Maximum BPM | `200` |
| `--no-hpss` | Disable percussive separation | Off |
| `--no-snap` | Disable intelligent BPM snapping | Off |
| `--json` | JSON output | Off |
| `--variations` | Show tempo variations | Off |

Examples:

```bash
python bpm_detect.py my_track.mp3
python bpm_detect.py my_track.mp3 --start 30 --duration 60
python bpm_detect.py my_track.mp3 --json
python bpm_detect.py dnb_track.flac --min-bpm 140 --max-bpm 190 --hop-length 64
```

## Build

See [BUILDING.md](BUILDING.md) for complete build and packaging instructions.

Quick commands:

```bash
# Linux
./scripts/build_linux.sh
```

```powershell
# Windows
.\scripts\build_windows.ps1

# Windows installer (.exe setup)
.\scripts\build_windows_installer.ps1
```

Note: an installer improves installation flow and shortcut behavior, but SmartScreen warnings can still appear on unsigned releases.

## Project Layout

```text
bpm-detector/
├── bpm_gui.py                  # Desktop GUI (single runtime profile)
├── bpm_gui_fast.py             # Thin compatibility wrapper; no second GUI implementation
├── bpm_detector.py             # Core BPM detection engine
├── bpm_detect.py               # CLI
├── scripts/                    # Build scripts
├── packaging/                  # Packaging assets and ffmpeg locations
└── packaging/windows/          # Inno Setup installer script
```

## Changelog

### v1.4.0

- Removed the legacy Flask web app scaffold to focus on maintained desktop GUI/CLI workflows
- Deleted unused web files and dependency references (`app.py`, `templates/`, `static/`, `flask`)
- Refined desktop footer branding with clearer social links and updated author line

### v1.3.7

- Header UI refresh: cleaner branding and compact monochrome website/GitHub/LinkedIn icons
- Window title now shows app name + version only
- Added SHA256 checksum generation and publication (`checksums.txt`) in release workflow
- Removed optional paid-code-signing workflow/docs to keep release pipeline simple

### v1.3.6

- Fixed Windows installer CI false-negative by removing fragile ISPP source precheck
- Source folder validation remains enforced in `build_windows_installer.ps1`

### v1.3.5

- Fixed Windows installer CI path resolution by passing absolute `SourceDir`/`OutputDir` to ISCC
- No runtime behavior change in the app

### v1.3.4

- Fixed PowerShell parser error in `build_windows_installer.ps1` (`CmdletBinding` placement)
- No runtime behavior change in the application itself

### v1.3.3

- Unified desktop packaging to a single runtime profile
- Removed legacy/full build branches and obsolete fallback spec
- Kept `bpm_gui_fast.py` as compatibility launcher to avoid breaking older scripts

### v1.3.2

- Removed the Windows `.cmd` launcher from packaged artifacts
- Keep direct startup via `BPM-detector.exe` after full ZIP extraction
- No functional changes to the Windows executable itself
- Updated README/build docs/release notes for the new Windows flow

### v1.3.1

- Added multi-file selection in desktop GUI file picker (`Ctrl/Cmd+click`)
- Updated docs and release notes to English
- Version bump and release metadata refresh

### v1.2.8

- Windows startup reliability improvements for packaged executable

### v1.2.5

- Linux packaging stability improvements (NumPy/OpenBLAS alignment issues)

## License

This project is released under the MIT License. See [LICENSE](LICENSE).

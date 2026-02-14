# BPM Detector Pro

High-precision BPM detection for audio files with a modern desktop GUI, CLI, and web UI.

![Version](https://img.shields.io/badge/version-1.3.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)

## Features

- High-precision BPM detection (hybrid autocorrelation + beat analysis)
- Fast desktop GUI startup (optimized Tkinter app)
- Multi-file batch selection from the GUI (`Fichiers...` supports Ctrl/Cmd+click)
- Folder analysis mode for full-library scans
- CLI mode for automation and scripting
- Web UI (Flask) for browser-based usage
- Portable binaries with bundled FFmpeg (no system FFmpeg required in release artifacts)
- Supports common formats: MP3, FLAC, WAV, M4A, OGG, AAC, and more

## Quick Start

### Option 1: Portable Binaries (Recommended)

Download artifacts from [GitHub Releases](../../releases):

- Linux: `BPM-Detector-Pro-Linux-x64`
- Windows: `BPM-Detector-Pro-Windows-x64.zip`
- macOS: `BPM-Detector-Pro-macOS.dmg`

Windows note:

- Extract the full ZIP folder before launching.
- Start with `START-BPM-Detector-Pro.cmd` (recommended) or `BPM-Detector-Pro.exe`.
- Do not move only the `.exe` without the `_internal` directory.

### Option 2: Run from Source

```bash
git clone https://github.com/YOUR_USER/bpm-detector.git
cd bpm-detector

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

If running from source, make sure FFmpeg is installed or available through `FFMPEG_BINARY` / `FFMPEG_PATH`.

## Usage

### Desktop GUI

```bash
python bpm_gui.py
# or use packaged binary
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

### Web UI

```bash
python app.py
```

Then open `http://127.0.0.1:5000`.

## Build

See [BUILDING.md](BUILDING.md) for full build and packaging instructions.

Quick commands:

```bash
# Linux
./scripts/build_linux.sh
```

```powershell
# Windows
.\scripts\build_windows.ps1
```

## Project Layout

```text
bpm-detector/
├── bpm_gui.py                  # Desktop GUI (full mode)
├── bpm_gui_fast.py             # Desktop GUI (fast startup mode)
├── bpm_detector.py             # Core BPM detection engine
├── bpm_detect.py               # CLI
├── app.py                      # Flask web app
├── scripts/                    # Build scripts
├── packaging/                  # Packaging assets and ffmpeg locations
├── static/                     # Web static assets
└── templates/                  # Web templates
```

## Changelog

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

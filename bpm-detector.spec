# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

# Detect platform for FFmpeg bundling
target_os = sys.platform
if target_os.startswith('linux'):
    os_name = 'linux'
    ffmpeg_exe = 'ffmpeg'
elif target_os == 'darwin':
    os_name = 'macos'
    ffmpeg_exe = 'ffmpeg'
elif target_os == 'win32':
    os_name = 'windows'
    ffmpeg_exe = 'ffmpeg.exe'
else:
    os_name = 'linux'
    ffmpeg_exe = 'ffmpeg'

base_dir = os.path.abspath('.')
ffmpeg_src = os.path.join(base_dir, 'packaging', 'ffmpeg', os_name, ffmpeg_exe)

# Verify source exists
if not os.path.exists(ffmpeg_src):
    print(f"WARNING: FFmpeg binary not found at {ffmpeg_src}")
    binaries = []
else:
    binaries = [(ffmpeg_src, '.')] # Put it in the root of the app

datas = []
hiddenimports = []

# Collect dependencies
datas += collect_data_files('librosa')
datas += collect_data_files('soundfile')
binaries += collect_dynamic_libs('soundfile')
hiddenimports += collect_submodules('librosa')
hiddenimports += collect_submodules('soundfile')

# Check for python DLLs explicitly (both python3.dll and version-specific like python311.dll)
python_dir = os.path.dirname(sys.executable)
base_dir = sys.base_prefix
version_str = f"{sys.version_info.major}{sys.version_info.minor}"
dll_names = ['python3.dll', f'python{version_str}.dll']

search_paths = [
    python_dir,
    os.path.join(python_dir, '..'), # Common in venv
    base_dir,
    os.path.join(base_dir, 'DLLs'),
    sys.prefix,
]

for dll_name in dll_names:
    found = False
    for path in search_paths:
        dll_path = os.path.join(path, dll_name)
        if os.path.exists(dll_path):
            print(f"Found {dll_name} at {dll_path}, adding to binaries...")
            binaries.append((dll_path, '.'))
            found = True
            break
    if not found:
        print(f"WARNING: Could not find {dll_name} in standard locations.")

a = Analysis(
    ['bpm_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['IPython', 'matplotlib', 'notebook'], # Smaller build
    win_no_prefer_redirects=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BPM-Detector-Pro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python*.dll', 'libffi*.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # Add icon path here if available
)

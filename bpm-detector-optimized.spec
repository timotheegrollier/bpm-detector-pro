# -*- mode: python ; coding: utf-8 -*-
"""
Optimized PyInstaller spec for minimal size and fast startup.
Target: < 50MB binary with < 5s cold start.
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

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
    binaries = [(ffmpeg_src, '.')]

# Minimal data collection - only soundfile libs
datas = []
binaries += collect_dynamic_libs('soundfile')

# Aggressive exclusions to minimize bundle size
# These are not needed for BPM detection
EXCLUDES = [
    # Heavy ML/scientific packages not needed
    'matplotlib',
    'IPython',
    'notebook',
    'jupyter',
    'PIL',
    'cv2',
    'tensorflow',
    'torch',
    'keras',
    'sklearn',
    'pandas',
    
    # Numba JIT compiler (huge, not critical for our use case)
    'numba',
    'llvmlite',
    
    # Testing frameworks
    'pytest',
    'unittest',
    'nose',
    
    # Documentation
    'sphinx',
    'docutils',
    
    # Unused scipy submodules
    'scipy.spatial.transform',
    'scipy.io.matlab',
    'scipy.io.arff',
    'scipy.io.netcdf',
    'scipy.io.harwell_boeing',
    'scipy.sparse.linalg._isolve',
    'scipy.sparse.linalg._eigen',
    
    # Unused numpy extras
    'numpy.distutils',
    'numpy.f2py',
    'numpy.testing',
    
    # Network/web (we only use local files)
    'http',
    'urllib3',
    'requests',
    'email',
    'html',
    'xml',
    
    # Flask (not needed for GUI)
    'flask',
    'werkzeug',
    'jinja2',
    'click',
    
    # Debug/dev tools
    'pdb',
    'trace',
    'cProfile',
    'profile',
    
    # Unused encodings (keep core ones)
    'encodings.idna',
    'encodings.punycode',
    
    # Other unused
    'curses',
    'asyncio',
    'concurrent.futures',
    'multiprocessing.popen_spawn_win32' if os_name != 'windows' else 'multiprocessing.popen_fork',
]

# Only the essential hidden imports
hiddenimports = [
    'soundfile',
    'numpy',
    'scipy.signal',
    'scipy.fft',
    'scipy.ndimage',
]

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
    ['bpm_gui_fast.py'],  # Use optimized GUI
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate binaries to save space
seen = set()
a.binaries = [x for x in a.binaries if not (x[0] in seen or seen.add(x[0]))]

# Remove unnecessary datas
a.datas = [x for x in a.datas if not any(
    exc in x[0] for exc in ['__pycache__', '.pyc', 'test', 'example', 'doc']
)]

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
    strip=True,  # Strip debug symbols
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python*.dll', 'libffi*.dll'],  # Don't compress critical DLLs
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

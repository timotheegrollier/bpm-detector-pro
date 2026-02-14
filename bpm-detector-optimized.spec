# -*- mode: python ; coding: utf-8 -*-
"""
Optimized PyInstaller spec for minimal size and fast startup.
Target: < 50MB binary with < 5s cold start.
"""
import os
import sys
import sysconfig
import glob
import subprocess
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
try:
    from PyInstaller.utils.hooks import get_python_library_path  # PyInstaller >= 6.3
except Exception:
    try:
        from PyInstaller.compat import get_python_library_path  # Older versions
    except Exception:
        def get_python_library_path():
            return None

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

# Sync version from git tag (best effort)
def _sync_version():
    script = os.path.join(base_dir, 'scripts', 'update_version.py')
    if os.path.exists(script):
        try:
            subprocess.run([sys.executable, script], check=False)
        except Exception:
            pass

_sync_version()

# Verify source exists
if not os.path.exists(ffmpeg_src):
    print(f"WARNING: FFmpeg binary not found at {ffmpeg_src}")
    binaries = []
else:
    binaries = [(ffmpeg_src, '.')]

# App icon (Windows prefers .ico)
icon_path = None
if os_name == 'windows':
    icon_candidate = os.path.join(base_dir, 'packaging', 'assets', 'bpm-detector.ico')
    if os.path.exists(icon_candidate):
        icon_path = icon_candidate
    else:
        print(f"WARNING: Icon not found at {icon_candidate}")
elif os_name == 'linux':
    icon_candidate = os.path.join(base_dir, 'packaging', 'assets', 'bpm-detector.png')
    if os.path.exists(icon_candidate):
        icon_path = icon_candidate

# Windows version info (embedded in .exe)
version_file = None
if os_name == 'windows':
    version_candidate = os.path.join(base_dir, 'packaging', 'pyinstaller', 'version_info.txt')
    if os.path.exists(version_candidate):
        version_file = version_candidate
    else:
        print(f"WARNING: Version info not found at {version_candidate}")

# WINDOWS: use onedir mode. DLLs are normal files on disk, no dynamic extraction,
# so Windows Defender / antivirus cannot block memory-mapped DLL loading.
# LINUX/MACOS: use onefile mode (no antivirus issues on these platforms).
use_onedir = (os_name == 'windows')

# Avoid UPX/strip on Linux (can break OpenBLAS/NumPy shared libs)
use_upx = True
use_strip = True
if os_name == 'linux':
    use_upx = False
    use_strip = False

UPX_EXCLUDE = [
    'vcruntime140.dll',
    'python*.dll',
    'libffi*.dll',
    'libscipy_openblas*.so*',
    'libopenblas*.so*',
]

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

    # Librosa (optional, large). Optimized build uses numpy-only fallback.
    'librosa',
    
    # Testing frameworks
    'pytest',
    'unittest',
    'nose',
    
    # Documentation
    'sphinx',
    'docutils',
    
    # Scipy (not used in optimized build)
    'scipy',
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
    'urllib3',
    'requests',
    'html',
    
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
]

def _add_python_dlls(binaries_list):
    if sys.platform != 'win32':
        return
    version_str = f"{sys.version_info.major}{sys.version_info.minor}"
    dll_names = [f'python{version_str}.dll', 'python3.dll']

    found_any = False
    def _add(path, note=None):
        nonlocal found_any
        if path and os.path.exists(path):
            if (path, '.') not in binaries_list:
                if note:
                    print(note)
                binaries_list.append((path, '.'))
            found_any = True
            return True
        return False

    # Allow explicit override via environment variables
    env_dll = os.environ.get('PYTHON_DLL')
    if env_dll:
        for raw in env_dll.split(os.pathsep):
            cand = raw.strip().strip('"')
            _add(cand, f"Using PYTHON_DLL: {cand}")

    env_dir = os.environ.get('PYTHON_DLL_DIR')
    if env_dir and os.path.isdir(env_dir):
        for name in dll_names:
            _add(os.path.join(env_dir, name), f"Found {name} via PYTHON_DLL_DIR: {env_dir}")

    # sysconfig hint for DLL name/path
    cfg_pydll = sysconfig.get_config_var('pythondll')
    if cfg_pydll:
        if os.path.isabs(cfg_pydll):
            _add(cfg_pydll, f"Found python DLL via sysconfig: {cfg_pydll}")
        else:
            if cfg_pydll not in dll_names:
                dll_names.append(cfg_pydll)

    # Best-effort: ask PyInstaller for the python DLL path first
    py_dll = get_python_library_path()
    _add(py_dll, f"Found python DLL via PyInstaller: {py_dll}" if py_dll else None)

    python_dir = os.path.dirname(sys.executable)
    base_prefix = sys.base_prefix
    search_paths = [
        python_dir,
        os.path.abspath(os.path.join(python_dir, '..')),  # Common in venv
        base_prefix,
        os.path.join(base_prefix, 'DLLs'),
        sys.prefix,
        os.path.join(sys.prefix, 'DLLs'),
    ]

    # Add sysconfig-based hints
    for var in ('BINDIR', 'DLLDIR', 'LIBDIR', 'installed_base', 'base', 'platbase'):
        val = sysconfig.get_config_var(var)
        if val:
            search_paths.append(val)

    # De-duplicate paths, keep order
    seen = set()
    search_paths = [p for p in search_paths if p and not (p in seen or seen.add(p))]

    for dll_name in dll_names:
        found = False
        for path in search_paths:
            dll_path = os.path.join(path, dll_name)
            if os.path.exists(dll_path):
                print(f"Found {dll_name} at {dll_path}, adding to binaries...")
                binaries_list.append((dll_path, '.'))
                found = True
                found_any = True
                break
        if not found:
            print(f"WARNING: Could not find {dll_name} in standard locations.")

    # Last resort: recursive search under base prefix
    if not found_any and base_prefix and os.path.exists(base_prefix):
        for dll_name in dll_names:
            matches = glob.glob(os.path.join(base_prefix, '**', dll_name), recursive=True)
            if matches:
                print(f"Found {dll_name} via recursive search at {matches[0]}, adding to binaries...")
                binaries_list.append((matches[0], '.'))
                found_any = True
                break

    if not found_any:
        raise SystemExit("ERROR: Python DLL not found. Set PYTHON_DLL or PYTHON_DLL_DIR and rebuild.")

_add_python_dlls(binaries)

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

if use_onedir:
    # ONEDIR mode for Windows: DLLs are real files on disk, no dynamic extraction.
    # This is the ONLY reliable way to avoid "Failed to load Python DLL" errors
    # caused by Windows Defender blocking memory-mapped DLL loading from temp dirs.
    exe = EXE(
        pyz,
        a.scripts,
        [],       # No binaries/datas in EXE for onedir
        exclude_binaries=True,
        name='BPM-Detector-Pro',
        debug=False,
        bootloader_ignore_signals=False,
        strip=use_strip,
        upx=use_upx,
        upx_exclude=UPX_EXCLUDE,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
        version=version_file,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=use_strip,
        upx=use_upx,
        upx_exclude=UPX_EXCLUDE,
        name='BPM-Detector-Pro',
    )
else:
    # ONEFILE mode for Linux/macOS (no antivirus issues on these platforms)
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
        strip=use_strip,
        upx=use_upx,
        upx_exclude=UPX_EXCLUDE,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
        version=version_file,
    )

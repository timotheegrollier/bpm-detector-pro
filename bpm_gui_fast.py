#!/usr/bin/env python3
"""
Desktop GUI for BPM detection - FAST STARTUP Version.

Key optimizations:
1. Lazy imports - librosa loaded only when analysis starts
2. Lightweight splash/progress feedback
3. Single-process analysis (faster startup, no fork overhead)
4. Minimal dependencies at import time
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk
from typing import Optional

# Lazy-loaded modules (heavy)
_librosa = None
_np = None
_sf = None


def _ensure_libs():
    """Load heavy libraries on first use."""
    global _librosa, _np, _sf
    if _librosa is None:
        import numpy as np
        import soundfile as sf
        # Note: We use a lightweight BPM detector instead of full librosa
        _np = np
        _sf = sf
        try:
            import librosa
            _librosa = librosa
        except ImportError:
            _librosa = None


def _lightweight_bpm_detect(file_path: str, options: dict) -> dict:
    """
    Lightweight BPM detection using only numpy/scipy + soundfile.
    Falls back to librosa if available for better accuracy.
    """
    _ensure_libs()
    
    import subprocess
    import tempfile
    
    # Find ffmpeg
    ffmpeg_path = _find_ffmpeg_fast()
    if not ffmpeg_path:
        raise RuntimeError("FFmpeg not found")
    
    # Decode to wav
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        cmd = [ffmpeg_path, "-v", "error", "-y", "-threads", "1"]
        start = options.get("start")
        duration = options.get("duration") or 45  # Analyze only 45s for speed
        
        if start:
            cmd += ["-ss", str(start)]
        cmd += ["-i", file_path]
        if duration:
            cmd += ["-t", str(duration)]
        cmd += ["-ac", "1", "-ar", "22050", "-f", "wav", tmp_path]
        
        # Hide console on Windows
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, check=True, startupinfo=startupinfo, 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(cmd, check=True, 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Load audio
        y, sr = _sf.read(tmp_path)
        if y.ndim > 1:
            y = _np.mean(y, axis=1)
        
        # Use librosa if available (more accurate)
        if _librosa is not None:
            bpm = _estimate_bpm_librosa(y, sr, options)
        else:
            bpm = _estimate_bpm_scipy(y, sr, options)
        
        # Snap to integer if close
        snap = options.get("snap_bpm", True)
        if snap:
            rounded = round(bpm)
            if abs(bpm - rounded) < 1.1:
                bpm = float(rounded)
        
        return {"status": "ok", "bpm": bpm}
        
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def _estimate_bpm_librosa(y, sr: int, options: dict) -> float:
    """Use librosa for accurate BPM detection."""
    hop_length = 128
    min_bpm = options.get("min_bpm", 60)
    max_bpm = options.get("max_bpm", 200)
    
    # Onset envelope
    onset_env = _librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length, fmax=8000)
    
    if onset_env.size == 0:
        raise RuntimeError("Cannot estimate tempo")
    
    # Autocorrelation for tempo
    ac = _librosa.autocorrelate(onset_env, max_size=None)
    
    min_lag = int(60.0 * sr / (hop_length * max_bpm))
    max_lag = int(60.0 * sr / (hop_length * min_bpm))
    max_lag = min(max_lag, ac.size - 1)
    
    if min_lag >= ac.size:
        return float(min_bpm)
    
    search_range = ac[min_lag:max_lag + 1]
    if search_range.size == 0:
        return float(min_bpm)
    
    best_idx = _np.argmax(search_range) + min_lag
    
    # Check harmonic at half lag
    half_lag = best_idx // 2
    if half_lag >= min_lag:
        win = 2
        start = max(0, half_lag - win)
        end = min(ac.size, half_lag + win + 1)
        local_max_idx = _np.argmax(ac[start:end]) + start
        if ac[local_max_idx] > ac[best_idx] * 0.6:
            best_idx = local_max_idx
    
    # Parabolic interpolation
    if 0 < best_idx < ac.size - 1:
        y0, y1, y2 = ac[best_idx - 1:best_idx + 2]
        denom = y0 - 2 * y1 + y2
        if abs(denom) > 1e-10:
            best_lag = best_idx + 0.5 * (y0 - y2) / denom
        else:
            best_lag = float(best_idx)
    else:
        best_lag = float(best_idx)
    
    bpm = 60.0 * sr / (hop_length * best_lag)
    
    # Beat tracking refinement
    try:
        tempo, _ = _librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length, 
                                            start_bpm=bpm, tightness=400)
        # Average if close
        if abs(bpm - tempo) < 5.0:
            bpm = (bpm + tempo) / 2.0
    except:
        pass
    
    return bpm


def _estimate_bpm_scipy(y, sr: int, options: dict) -> float:
    """Fallback BPM detection using only scipy (no librosa)."""
    from scipy import signal
    from scipy.fft import rfft, rfftfreq
    
    min_bpm = options.get("min_bpm", 60)
    max_bpm = options.get("max_bpm", 200)
    
    # Simple onset detection via spectral flux
    hop = 512
    win = 1024
    n_frames = (len(y) - win) // hop
    
    if n_frames < 10:
        return float(min_bpm)
    
    # Compute spectral flux
    prev_spec = _np.zeros(win // 2 + 1)
    onset_env = _np.zeros(n_frames)
    
    for i in range(n_frames):
        frame = y[i * hop:i * hop + win] * _np.hanning(win)
        spec = _np.abs(rfft(frame))
        
        # Spectral flux (only positive differences)
        diff = spec - prev_spec
        onset_env[i] = _np.sum(diff[diff > 0])
        prev_spec = spec
    
    # Autocorrelation
    ac = _np.correlate(onset_env, onset_env, mode='full')
    ac = ac[len(ac) // 2:]  # Keep positive lags only
    
    # BPM range to lag range
    frame_rate = sr / hop
    min_lag = int(frame_rate * 60 / max_bpm)
    max_lag = int(frame_rate * 60 / min_bpm)
    max_lag = min(max_lag, len(ac) - 1)
    
    if min_lag >= len(ac) or min_lag >= max_lag:
        return float(min_bpm)
    
    search = ac[min_lag:max_lag + 1]
    best_idx = _np.argmax(search) + min_lag
    
    bpm = frame_rate * 60 / best_idx
    return bpm


def _find_ffmpeg_fast() -> Optional[str]:
    """Fast ffmpeg lookup."""
    import shutil
    
    # Check environment
    env_path = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BINARY")
    if env_path and os.path.isfile(env_path):
        return env_path
    
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    
    # Check next to executable (PyInstaller bundle)
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        candidate = os.path.join(base, exe)
        if os.path.isfile(candidate):
            return candidate
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = os.path.join(meipass, exe)
            if os.path.isfile(candidate):
                return candidate
    
    # Check local paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for subdir in ["", "packaging/ffmpeg/windows", "packaging/ffmpeg/linux"]:
        candidate = os.path.join(base_dir, subdir, exe)
        if os.path.isfile(candidate):
            return candidate
    
    return shutil.which("ffmpeg")


class BPMApp(tk.Tk):
    """Main application with fast startup."""
    
    def __init__(self) -> None:
        super().__init__()
        self.title("BPM Detector Pro")
        self.geometry("1024x768")
        
        # Maximize window
        if sys.platform.startswith("linux"):
            self.attributes("-zoomed", True)
        else:
            self.state("zoomed")
        
        self.bind("<Escape>", lambda e: self.state("normal"))
        self.minsize(800, 600)
        
        # Settings variables
        self.start_var = tk.StringVar()
        self.duration_var = tk.StringVar()
        self.sr_var = tk.StringVar(value="22050")
        self.min_bpm_var = tk.StringVar(value="60")
        self.max_bpm_var = tk.StringVar(value="200")
        self.use_hpss_var = tk.BooleanVar(value=True)
        self.snap_var = tk.BooleanVar(value=True)
        
        self._queue = queue.Queue()
        self._active_tasks = 0
        self._libs_loaded = False
        
        self._init_theme()
        self._build_ui()
        
        # Pre-load libraries in background after UI is shown
        self.after(100, self._preload_libs)
    
    def _preload_libs(self) -> None:
        """Load heavy libraries in background thread."""
        def loader():
            try:
                _ensure_libs()
                self._queue.put(("libs_loaded", None))
            except Exception as e:
                self._queue.put(("libs_error", str(e)))
        
        threading.Thread(target=loader, daemon=True).start()
        self._check_libs_loading()
    
    def _check_libs_loading(self) -> None:
        """Check if libraries finished loading."""
        try:
            msg = self._queue.get_nowait()
            if msg[0] == "libs_loaded":
                self._libs_loaded = True
                self._set_status("Système prêt.")
            elif msg[0] == "libs_error":
                self._set_status(f"Erreur init: {msg[1]}", error=True)
        except queue.Empty:
            self._set_status("Chargement des librairies...")
            self.after(100, self._check_libs_loading)
    
    def _init_theme(self) -> None:
        self.colors = {
            "bg": "#0B0F19",
            "panel": "#111827",
            "card": "#1F2937",
            "text": "#F9FAFB",
            "muted": "#9CA3AF",
            "accent": "#38BDF8",
            "accent_dark": "#0EA5E9",
            "danger": "#EF4444",
            "success": "#10B981"
        }
        
        self.configure(bg=self.colors["bg"])
        style = ttk.Style(self)
        style.theme_use("clam")
        
        family = self._pick_font_family()
        self.font_title = tkfont.Font(family=family, size=20, weight="bold")
        self.font_label = tkfont.Font(family=family, size=10)
        self.font_mono = tkfont.Font(family="Monospace", size=10)
        
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Panel.TFrame", background=self.colors["panel"], relief="flat")
        style.configure("Header.TLabel", background=self.colors["bg"], 
                       foreground=self.colors["text"], font=self.font_title)
        style.configure("TLabel", background=self.colors["panel"], 
                       foreground=self.colors["text"], font=self.font_label)
        style.configure("Accent.TButton", background=self.colors["accent"], 
                       foreground=self.colors["bg"], font=self.font_label, 
                       padding=(20, 10))
        style.map("Accent.TButton", 
                 background=[("active", self.colors["accent_dark"]), 
                           ("disabled", "#374151")])
        
        style.configure("Treeview", background="#111827", fieldbackground="#111827", 
                       foreground=self.colors["text"], rowheight=32)
        style.configure("Treeview.Heading", background="#1F2937", 
                       foreground=self.colors["muted"], font=self.font_label, 
                       relief="flat")
    
    def _pick_font_family(self) -> str:
        if sys.platform.startswith("win"):
            return "Segoe UI"
        if sys.platform == "darwin":
            return "SF Pro Text"
        return "Cantarell"
    
    def _build_ui(self) -> None:
        # Header
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=30, pady=(25, 10))
        
        title_box = ttk.Frame(header, style="TFrame")
        title_box.pack(side="left")
        ttk.Label(title_box, text="BPM Detector", style="Header.TLabel").pack(anchor="w")
        tk.Label(title_box, text="Studio Grade Analysis", bg=self.colors["bg"], 
                fg=self.colors["accent"], font=(self._pick_font_family(), 9, "bold")).pack(anchor="w")
        
        self.gear_btn = tk.Button(
            header, text="⚙", command=self._open_settings,
            bg=self.colors["bg"], fg=self.colors["muted"], font=("Arial", 18),
            bd=0, activebackground=self.colors["bg"], 
            activeforeground=self.colors["accent"], cursor="hand2"
        )
        self.gear_btn.pack(side="right", pady=5)
        
        # Main content
        content = ttk.Frame(self, style="TFrame")
        content.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Left panel
        left = ttk.Frame(content, style="Panel.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.path_var = tk.StringVar()
        drop_area = tk.Frame(left, bg=self.colors["card"], bd=1, 
                            relief="solid", height=180)
        drop_area.pack(fill="x", padx=20, pady=20)
        drop_area.pack_propagate(False)
        
        tk.Label(drop_area, text="SÉLECTIONNEZ VOS FICHIERS", 
                bg=self.colors["card"], fg=self.colors["muted"], 
                font=(self._pick_font_family(), 10, "bold")).pack(expand=True, pady=(20, 0))
        
        btn_row = tk.Frame(drop_area, bg=self.colors["card"])
        btn_row.pack(expand=True)
        
        tk.Button(btn_row, text="Fichiers...", command=self._browse_file, 
                 bg=self.colors["accent"], fg=self.colors["bg"], bd=0, 
                 padx=15, pady=5, font=self.font_label, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_row, text="Dossier...", command=self._browse_directory, 
                 bg=self.colors["panel"], fg=self.colors["text"], bd=0, 
                 padx=15, pady=5, font=self.font_label, cursor="hand2").pack(side="left", padx=5)
        
        self.path_label = tk.Label(left, textvariable=self.path_var, 
                                  bg=self.colors["panel"], fg=self.colors["accent"], 
                                  font=self.font_label, wraplength=400)
        self.path_label.pack(fill="x", padx=20)
        
        self.analyze_btn = ttk.Button(left, text="LANCER L'ANALYSE", 
                                     style="Accent.TButton", command=self._start_analysis)
        self.analyze_btn.pack(fill="x", padx=20, pady=20)
        
        # BPM display
        self.bpm_var = tk.StringVar(value="--")
        res_box = tk.Frame(left, bg=self.colors["bg"], pady=10)
        res_box.pack(fill="x", padx=20)
        tk.Label(res_box, text="DERNIER RÉSULTAT", bg=self.colors["bg"], 
                fg=self.colors["muted"], font=(self._pick_font_family(), 8, "bold")).pack()
        tk.Label(res_box, textvariable=self.bpm_var, bg=self.colors["bg"], 
                fg=self.colors["text"], font=(self._pick_font_family(), 48, "bold")).pack()
        tk.Label(res_box, text="BPM", bg=self.colors["bg"], fg=self.colors["accent"], 
                font=(self._pick_font_family(), 10, "bold")).pack()
        
        # Right panel - file list
        right = ttk.Frame(content, style="Panel.TFrame")
        right.pack(side="right", fill="both", expand=True)
        
        top_right = ttk.Frame(right, style="Panel.TFrame")
        top_right.pack(fill="x", padx=20, pady=(20, 10))
        ttk.Label(top_right, text="FILE D'ATTENTE", 
                 font=(self._pick_font_family(), 9, "bold")).pack(side="left")
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(top_right, variable=self.progress_var, 
                                           maximum=100, length=200)
        self.progress_bar.pack(side="right")
        
        table_frame = ttk.Frame(right, style="Panel.TFrame")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.tracks_tree = ttk.Treeview(table_frame, 
                                        columns=("name", "bpm", "status"), 
                                        show="headings", selectmode="browse")
        self.tracks_tree.heading("name", text="NOM")
        self.tracks_tree.heading("bpm", text="BPM")
        self.tracks_tree.heading("status", text="STATUT")
        self.tracks_tree.column("name", width=250)
        self.tracks_tree.column("bpm", width=70, anchor="center")
        self.tracks_tree.column("status", width=90, anchor="center")
        
        sb = ttk.Scrollbar(table_frame, orient="vertical", 
                          command=self.tracks_tree.yview)
        self.tracks_tree.configure(yscrollcommand=sb.set)
        self.tracks_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        # Status bar
        self.status_var = tk.StringVar(value="Initialisation...")
        self.status_label = tk.Label(self, textvariable=self.status_var, 
                                    bg=self.colors["bg"], fg=self.colors["muted"], 
                                    font=(self._pick_font_family(), 9), 
                                    anchor="w", padx=30, pady=10)
        self.status_label.pack(fill="x")
    
    def _open_settings(self) -> None:
        """Open settings dialog."""
        SettingsDialog(self)
    
    def _browse_file(self) -> None:
        home = os.path.expanduser("~")
        p = filedialog.askopenfilename(
            title="Audio",
            initialdir=home,
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.m4a *.ogg"), ("All", "*.*")]
        )
        if p:
            self.path_var.set(p)
    
    def _browse_directory(self) -> None:
        home = os.path.expanduser("~")
        p = filedialog.askdirectory(title="Dossier", initialdir=home)
        if p:
            self.path_var.set(p)
    
    def _collect_options(self) -> dict:
        def to_f(v):
            return float(v.replace(",", ".")) if v.strip() else None
        
        return {
            "start": to_f(self.start_var.get()),
            "duration": to_f(self.duration_var.get()),
            "sample_rate": int(self.sr_var.get()),
            "min_bpm": to_f(self.min_bpm_var.get()) or 60,
            "max_bpm": to_f(self.max_bpm_var.get()) or 200,
            "use_hpss": self.use_hpss_var.get(),
            "snap_bpm": self.snap_var.get()
        }
    
    def _start_analysis(self) -> None:
        if self._active_tasks > 0:
            return
        
        if not self._libs_loaded:
            self._set_status("Librairies en cours de chargement...", error=True)
            return
        
        path = self.path_var.get().strip()
        if not path:
            self._set_status("Aucun fichier sélectionné.", error=True)
            return
        
        self._set_status("Préparation...")
        self.analyze_btn.configure(state="disabled")
        self.tracks_tree.delete(*self.tracks_tree.get_children())
        self.progress_var.set(0)
        
        # Collect files
        files = []
        if os.path.isdir(path):
            exts = (".wav", ".mp3", ".flac", ".m4a", ".ogg")
            files = [os.path.join(path, f) for f in sorted(os.listdir(path)) 
                    if f.lower().endswith(exts)]
        else:
            files = [path]
        
        if not files:
            self._set_status("Aucun fichier valide.", error=True)
            self.analyze_btn.configure(state="normal")
            return
        
        for f in files:
            self.tracks_tree.insert("", "end", iid=f, 
                                   values=(os.path.basename(f), "--", "Prêt"))
        
        self._active_tasks = len(files)
        options = self._collect_options()
        
        # Use single thread for analysis (faster startup, no fork overhead)
        threading.Thread(target=self._run_analysis, 
                        args=(files, options), daemon=True).start()
        self.after(100, self._poll_queue)
    
    def _run_analysis(self, files: list, options: dict) -> None:
        """Run analysis sequentially in background thread."""
        total = len(files)
        
        for i, f in enumerate(files):
            if self._active_tasks == 0:
                break
            
            self._queue.put(("status", f, "Analyse..."))
            
            try:
                result = _lightweight_bpm_detect(f, options)
                if result["status"] == "ok":
                    self._queue.put(("ok", f, result["bpm"], total))
                else:
                    self._queue.put(("err", f, "Échec", total))
            except Exception as e:
                self._queue.put(("err", f, str(e), total))
    
    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                mtype, path = msg[0], msg[1]
                
                if mtype == "status":
                    self.tracks_tree.item(path, 
                                         values=(os.path.basename(path), "--", msg[2]))
                elif mtype == "ok":
                    bpm = f"{msg[2]:.1f}"
                    self.tracks_tree.item(path, 
                                         values=(os.path.basename(path), bpm, "Terminé"))
                    self.bpm_var.set(bpm)
                    self._update_progress(msg[3])
                elif mtype == "err":
                    self.tracks_tree.item(path, 
                                         values=(os.path.basename(path), "ERR", "Échec"))
                    self._update_progress(msg[3])
                    
        except queue.Empty:
            if self._active_tasks > 0:
                self.after(100, self._poll_queue)
    
    def _update_progress(self, total: int) -> None:
        self._active_tasks -= 1
        self.progress_var.set(((total - self._active_tasks) / total) * 100)
        if self._active_tasks == 0:
            self.analyze_btn.configure(state="normal")
            self._set_status("Analyse terminée.")
    
    def _set_status(self, msg: str, error: bool = False) -> None:
        self.status_var.set(msg)
        self.status_label.configure(
            fg=self.colors["danger"] if error else self.colors["muted"]
        )


class SettingsDialog(tk.Toplevel):
    """Settings dialog."""
    
    def __init__(self, parent: BPMApp) -> None:
        super().__init__(parent)
        self.title("Configuration")
        self.geometry("400x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.parent = parent
        self.colors = parent.colors
        self.configure(bg=self.colors["bg"])
        
        container = ttk.Frame(self, style="TFrame")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(container, text="RÉGLAGES EXPERTS", 
                 style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        grid = ttk.Frame(container, style="TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        
        self._labeled_entry(grid, "Début (s)", parent.start_var, 0, 0)
        self._labeled_entry(grid, "Durée (s)", parent.duration_var, 0, 1)
        self._labeled_entry(grid, "Sample rate", parent.sr_var, 1, 0)
        self._labeled_entry(grid, "BPM min", parent.min_bpm_var, 1, 1)
        self._labeled_entry(grid, "BPM max", parent.max_bpm_var, 2, 0)
        
        toggles = ttk.Frame(container, style="TFrame")
        toggles.pack(fill="x", pady=20)
        ttk.Checkbutton(toggles, text="Mode Percussions (HPSS)", 
                       variable=parent.use_hpss_var).pack(anchor="w")
        ttk.Checkbutton(toggles, text="Arrondir les résultats", 
                       variable=parent.snap_var).pack(anchor="w", pady=(8, 0))
        
        ttk.Button(container, text="Fermer", 
                  command=self.destroy).pack(side="bottom", fill="x", pady=(20, 0))
    
    def _labeled_entry(self, parent: ttk.Frame, label: str, 
                       var: tk.StringVar, row: int, column: int) -> None:
        block = ttk.Frame(parent, style="TFrame")
        block.grid(row=row, column=column, sticky="ew", padx=5, pady=5)
        tk.Label(block, text=label, bg=self.colors["bg"], 
                fg=self.colors["muted"], font=("Cantarell", 9)).pack(anchor="w")
        ttk.Entry(block, textvariable=var).pack(fill="x", pady=(4, 0))


if __name__ == "__main__":
    app = BPMApp()
    app.mainloop()

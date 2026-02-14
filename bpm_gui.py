#!/usr/bin/env python3
"""Desktop GUI for BPM detection - Clean & Pro Version."""

from __future__ import annotations

import os
import queue
import sys
import threading
import multiprocessing
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk
from typing import Optional, Callable

from app_version import APP_VERSION

def analysis_worker(file_path: str, options: dict) -> dict:
    """Top-level worker for ProcessPoolExecutor to avoid GUI crashes."""
    # We can't use the GUI-linked callback here across processes easily,
    # so we'll return the final result. Progress is handled by task completion.
    try:
        from bpm_detector import detect_bpm_details
        # We wrap the detector to return a clean dict
        res = detect_bpm_details(file_path, **{k:v for k,v in options.items() if k != 'path'})
        return {"status": "ok", "file": file_path, "bpm": res["bpm"]}
    except Exception as e:
        return {"status": "err", "file": file_path, "error": traceback.format_exc()}

class SettingsDialog(tk.Toplevel):
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
        
        # Build settings UI
        container = ttk.Frame(self, style="TFrame")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(container, text="RÉGLAGES EXPERTS", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        # Grid for numeric inputs
        grid = ttk.Frame(container, style="TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self._labeled_entry(grid, "Début (s)", parent.start_var, 0, 0)
        self._labeled_entry(grid, "Durée (s)", parent.duration_var, 0, 1)
        self._labeled_entry(grid, "Sample rate", parent.sr_var, 1, 0)
        self._labeled_entry(grid, "BPM min", parent.min_bpm_var, 1, 1)
        self._labeled_entry(grid, "BPM max", parent.max_bpm_var, 2, 0)

        # Toggles
        toggles = ttk.Frame(container, style="TFrame")
        toggles.pack(fill="x", pady=20)
        ttk.Checkbutton(toggles, text="Mode Percussions (HPSS)", variable=parent.use_hpss_var).pack(anchor="w")
        ttk.Checkbutton(toggles, text="Arrondir les résultats", variable=parent.snap_var).pack(anchor="w", pady=(8, 0))
        
        ttk.Button(container, text="Fermer", command=self.destroy).pack(side="bottom", fill="x", pady=(20, 0))

    def _labeled_entry(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int, column: int) -> None:
        block = ttk.Frame(parent, style="TFrame")
        block.grid(row=row, column=column, sticky="ew", padx=5, pady=5)
        self.parent.status_label # Just to ensure we have parent ref
        tk.Label(block, text=label, bg=self.colors["bg"], fg=self.colors["muted"], font=("Cantarell", 9)).pack(anchor="w")
        ttk.Entry(block, textvariable=var).pack(fill="x", pady=(4, 0))


class BPMApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"BPM Detector Pro v{APP_VERSION}")
        self.geometry("1024x768") # Default fallback
        # "Fullscreen modified" = Maximized (still has taskbar/titlebar)
        if sys.platform.startswith("linux"):
            self.attributes("-zoomed", True)
        else:
            self.state("zoomed")
        
        self.bind("<Escape>", lambda e: self.state("normal"))
        self.minsize(800, 600)

        # Global variables for settings
        self.start_var = tk.StringVar()
        self.duration_var = tk.StringVar()
        self.sr_var = tk.StringVar(value="22050") # Perfect Cali & Fast
        self.min_bpm_var = tk.StringVar(value="60")
        self.max_bpm_var = tk.StringVar(value="200")
        self.use_hpss_var = tk.BooleanVar(value=True)
        self.snap_var = tk.BooleanVar(value=True)

        self._queue = queue.Queue()
        self._active_tasks = 0
        self._cancel_analysis = False
        self.selected_files: list[str] = []

        self._init_theme()
        self._build_ui()

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
        style.configure("Header.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=self.font_title)
        style.configure("TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=self.font_label)
        style.configure("Accent.TButton", background=self.colors["accent"], foreground=self.colors["bg"], font=self.font_label, padding=(20, 10))
        style.map("Accent.TButton", background=[("active", self.colors["accent_dark"]), ("disabled", "#374151")])
        
        style.configure("Treeview", background="#111827", fieldbackground="#111827", foreground=self.colors["text"], rowheight=32)
        style.configure("Treeview.Heading", background="#1F2937", foreground=self.colors["muted"], font=self.font_label, relief="flat")

    def _pick_font_family(self) -> str:
        if sys.platform.startswith("win"): return "Segoe UI"
        if sys.platform == "darwin": return "SF Pro Text"
        return "Cantarell"

    def _build_ui(self) -> None:
        # Header with gear icon
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=30, pady=(25, 10))
        
        title_box = ttk.Frame(header, style="TFrame")
        title_box.pack(side="left")
        ttk.Label(title_box, text="BPM Detector", style="Header.TLabel").pack(anchor="w")
        tk.Label(title_box, text="Studio Grade Analysis", bg=self.colors["bg"], fg=self.colors["accent"], font=(self._pick_font_family(), 9, "bold")).pack(anchor="w")
        tk.Label(title_box, text=f"Version {APP_VERSION}", bg=self.colors["bg"],
                fg=self.colors["muted"], font=(self._pick_font_family(), 8, "normal")).pack(anchor="w")

        self.gear_btn = tk.Button(
            header, text="⚙", command=self._open_settings,
            bg=self.colors["bg"], fg=self.colors["muted"], font=("Arial", 18),
            bd=0, activebackground=self.colors["bg"], activeforeground=self.colors["accent"],
            cursor="hand2"
        )
        self.gear_btn.pack(side="right", pady=5)

        # Main Content
        content = ttk.Frame(self, style="TFrame")
        content.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Left: File Drop & Actions
        left = ttk.Frame(content, style="Panel.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.path_var = tk.StringVar()
        drop_area = tk.Frame(left, bg=self.colors["card"], bd=1, relief="solid", height=180)
        drop_area.pack(fill="x", padx=20, pady=20)
        drop_area.pack_propagate(False)
        
        tk.Label(drop_area, text="SÉLECTIONNEZ VOS FICHIERS", bg=self.colors["card"], fg=self.colors["muted"], font=(self._pick_font_family(), 10, "bold")).pack(expand=True, pady=(20, 0))
        
        btn_row = ttk.Frame(drop_area, style="Panel.TFrame")
        btn_row.configure(style="TFrame") # Match card bg better? No, let's just use tk.Frame
        btn_row = tk.Frame(drop_area, bg=self.colors["card"])
        btn_row.pack(expand=True)
        
        tk.Button(btn_row, text="Fichiers...", command=self._browse_file, bg=self.colors["accent"], fg=self.colors["bg"], bd=0, padx=15, pady=5, font=self.font_label, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_row, text="Dossier...", command=self._browse_directory, bg=self.colors["panel"], fg=self.colors["text"], bd=0, padx=15, pady=5, font=self.font_label, cursor="hand2").pack(side="left", padx=5)

        self.path_label = tk.Label(left, textvariable=self.path_var, bg=self.colors["panel"], fg=self.colors["accent"], font=self.font_label, wraplength=400)
        self.path_label.pack(fill="x", padx=20)

        self.analyze_btn = ttk.Button(left, text="LANCER L'ANALYSE", style="Accent.TButton", command=self._start_analysis)
        self.analyze_btn.pack(fill="x", padx=20, pady=20)

        # Result Display (Big Number)
        self.bpm_var = tk.StringVar(value="--")
        res_box = tk.Frame(left, bg=self.colors["bg"], pady=10)
        res_box.pack(fill="x", padx=20)
        tk.Label(res_box, text="DERNIER RÉSULTAT", bg=self.colors["bg"], fg=self.colors["muted"], font=(self._pick_font_family(), 8, "bold")).pack()
        tk.Label(res_box, textvariable=self.bpm_var, bg=self.colors["bg"], fg=self.colors["text"], font=(self._pick_font_family(), 48, "bold")).pack()
        tk.Label(res_box, text="BPM", bg=self.colors["bg"], fg=self.colors["accent"], font=(self._pick_font_family(), 10, "bold")).pack()

        # Right: List of tracks
        right = ttk.Frame(content, style="Panel.TFrame")
        right.pack(side="right", fill="both", expand=True)
        
        top_right = ttk.Frame(right, style="Panel.TFrame")
        top_right.pack(fill="x", padx=20, pady=(20, 10))
        ttk.Label(top_right, text="FILE D'ATTENTE", font=(self._pick_font_family(), 9, "bold")).pack(side="left")
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(top_right, variable=self.progress_var, maximum=100, length=200)
        self.progress_bar.pack(side="right")

        table_frame = ttk.Frame(right, style="Panel.TFrame")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.tracks_tree = ttk.Treeview(table_frame, columns=("name", "bpm", "status"), show="headings", selectmode="browse")
        self.tracks_tree.heading("name", text="NOM")
        self.tracks_tree.heading("bpm", text="BPM")
        self.tracks_tree.heading("status", text="STATUT")
        self.tracks_tree.column("name", width=250)
        self.tracks_tree.column("bpm", width=70, anchor="center")
        self.tracks_tree.column("status", width=90, anchor="center")
        
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tracks_tree.yview)
        self.tracks_tree.configure(yscrollcommand=sb.set)
        self.tracks_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Logs (copyable)
        logs = ttk.Frame(self, style="Panel.TFrame")
        logs.pack(fill="x", padx=30, pady=(0, 10))

        logs_header = ttk.Frame(logs, style="Panel.TFrame")
        logs_header.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(logs_header, text="LOGS",
                  font=(self._pick_font_family(), 9, "bold")).pack(side="left")
        tk.Button(
            logs_header, text="Copier", command=self._copy_logs,
            bg=self.colors["panel"], fg=self.colors["text"], bd=0,
            padx=10, pady=4, cursor="hand2"
        ).pack(side="right")

        logs_body = tk.Frame(logs, bg=self.colors["panel"])
        logs_body.pack(fill="both", padx=12, pady=(0, 12))

        self.log_text = tk.Text(
            logs_body,
            height=6,
            wrap="word",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=self.font_mono,
            bd=0
        )
        self.log_text.configure(state="disabled")
        self.log_text.tag_configure("error", foreground=self.colors["danger"])
        self.log_text.tag_configure("info", foreground=self.colors["text"])
        log_sb = ttk.Scrollbar(logs_body, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_sb.pack(side="right", fill="y")

        # Footer
        self.status_var = tk.StringVar(value="Système prêt.")
        self.status_label = tk.Label(self, textvariable=self.status_var, bg=self.colors["bg"], fg=self.colors["muted"], font=(self._pick_font_family(), 9), anchor="w", padx=30, pady=10)
        self.status_label.pack(fill="x")

    def _open_settings(self) -> None:
        SettingsDialog(self)

    def _browse_file(self) -> None:
        home = os.path.expanduser("~")
        paths = filedialog.askopenfilenames(
            title="Audio", 
            initialdir=home,
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.m4a *.ogg"), ("All", "*.*")]
        )
        if paths:
            self.selected_files = list(paths)
            if len(self.selected_files) == 1:
                self.path_var.set(self.selected_files[0])
            else:
                self.path_var.set(f"{len(self.selected_files)} fichiers sélectionnés")

    def _browse_directory(self) -> None:
        home = os.path.expanduser("~")
        p = filedialog.askdirectory(title="Dossier", initialdir=home)
        if p:
            self.selected_files = []
            self.path_var.set(p)

    def _collect_inputs(self) -> dict:
        path = self.path_var.get().strip()
        selected_files = [p for p in self.selected_files if p]
        if not path and not selected_files:
            raise ValueError("Aucun fichier sélectionné.")
        
        def to_f(v): return float(v.replace(",", ".")) if v.strip() else None
        
        return {
            "path": path,
            "selected_files": selected_files,
            "start": to_f(self.start_var.get()),
            "duration": to_f(self.duration_var.get()),
            "sample_rate": int(self.sr_var.get()),
            "min_bpm": to_f(self.min_bpm_var.get()),
            "max_bpm": to_f(self.max_bpm_var.get()),
            "use_hpss": self.use_hpss_var.get(),
            "snap_bpm": self.snap_var.get()
        }

    def _start_analysis(self) -> None:
        if self._active_tasks > 0: return
        try:
            payload = self._collect_inputs()
        except Exception as e:
            self._set_status(str(e), error=True)
            return

        self._set_status("Initialisation...")
        self.analyze_btn.configure(state="disabled")
        self.tracks_tree.delete(*self.tracks_tree.get_children())
        self.progress_var.set(0)

        path = payload["path"]
        selected_files = payload.get("selected_files") or []
        files = []
        if selected_files:
            # Keep order while removing duplicates.
            files = list(dict.fromkeys(selected_files))
        elif os.path.isdir(path):
            exts = (".wav", ".mp3", ".flac", ".m4a", ".ogg")
            files = [os.path.join(path, f) for f in sorted(os.listdir(path)) if f.lower().endswith(exts)]
        else:
            files = [path]

        if not files:
            self._set_status("Aucun fichier valide.", error=True)
            self.analyze_btn.configure(state="normal")
            return

        for f in files:
            self.tracks_tree.insert("", "end", iid=f, values=(os.path.basename(f), "--", "Prêt"))

        self._active_tasks = len(files)
        threading.Thread(target=self._run_batch_analysis, args=(files, payload), daemon=True).start()
        self.after(100, self._poll_queue)

    def _run_batch_analysis(self, files: list[str], options: dict) -> None:
        # Performance-Optimized Isolation: 2 process workers.
        # This provides the best speedup on modern multicore CPUs (Bazzite/Fedora)
        # while keeping the isolation benefits to prevent GUI crashes.
        with ProcessPoolExecutor(max_workers=2) as executor:
            for i, f in enumerate(files):
                if self._active_tasks == 0: break
                # Mark as processing in UI
                self._queue.put(("status_update", f, "Analyse..."))
                future = executor.submit(analysis_worker, f, options)
                future.add_done_callback(lambda fut, path=f, total=len(files): self._on_task_done(fut, path, total))

    def _on_task_done(self, future, path: str, total: int) -> None:
        try:
            res = future.result()
            if res["status"] == "ok":
                self._queue.put(("ok", path, res["bpm"], total))
            else:
                self._queue.put(("err", path, res["error"], total))
        except Exception as e:
            self._queue.put(("err", path, str(e), total))

    def _analyze_single(self, f: str, options: dict, idx: int, total: int) -> None:
        # Legacy method kept for single-track CLI compatibility if needed, 
        # but batch now uses top-level analysis_worker.
        pass

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                mtype, path = msg[0], msg[1]
                if mtype == "status_update":
                    self.tracks_tree.item(path, values=(os.path.basename(path), "--", msg[2]))
                elif mtype == "ok":
                    bpm = f"{msg[2]:.1f}"
                    self.tracks_tree.item(path, values=(os.path.basename(path), bpm, "Terminé"))
                    self.bpm_var.set(bpm)
                    self._update_progress(msg[3])
                elif mtype == "err":
                    self.tracks_tree.item(path, values=(os.path.basename(path), "ERR", "Échec"))
                    err = msg[2] or ""
                    summary = self._summarize_error(err)
                    if "numpy" in err.lower() or "numpy" in summary.lower():
                        summary = f"{summary} (problème d'installation de numpy)"
                    self._log(f"{os.path.basename(path)}: {summary}", error=True)
                    details = err.strip()
                    if details and details != summary:
                        self._log(details, error=True)
                    self._update_progress(msg[3])
        except queue.Empty:
            if self._active_tasks > 0: self.after(100, self._poll_queue)

    def _update_progress(self, total: int) -> None:
        self._active_tasks -= 1
        self.progress_var.set(((total - self._active_tasks) / total) * 100)
        if self._active_tasks == 0:
            self.analyze_btn.configure(state="normal")
            self._set_status("Analyse terminée.")

    def _set_status(self, msg: str, error=False) -> None:
        self.status_var.set(msg)
        self.status_label.configure(fg=self.colors["danger"] if error else self.colors["muted"])

    def _summarize_error(self, err: str) -> str:
        lines = [line.strip() for line in err.strip().splitlines() if line.strip()]
        return lines[-1] if lines else "Erreur inconnue"

    def _log(self, msg: str, error: bool = False) -> None:
        if not msg:
            return
        tag = "error" if error else "info"
        self.log_text.configure(state="normal")
        for line in msg.rstrip().splitlines():
            self.log_text.insert("end", line + "\n", tag)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _copy_logs(self) -> None:
        text = self.log_text.get("1.0", "end-1c")
        if not text.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Logs copiés.")


if __name__ == "__main__":
    # Required for PyInstaller bundle stability
    multiprocessing.freeze_support()
    
    # Force 'spawn' to avoid GUI/Thread conflicts on Linux/macOS
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

    app = BPMApp()
    app.mainloop()

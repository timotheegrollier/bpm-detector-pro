"""Core BPM detection utilities used by the CLI and desktop GUI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional, Callable

import librosa
import numpy as np
import soundfile as sf


def build_ffmpeg_cmd(
    ffmpeg_path: str,
    input_path: str,
    output_path: str,
    sample_rate: int,
    start: Optional[float],
    duration: Optional[float],
) -> list[str]:
    # Optimization: use fast-io flags, reduce complexity where possible for decoding
    cmd = [ffmpeg_path, "-v", "error", "-y", "-threads", "2"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", input_path]
    if duration is not None:
        cmd += ["-t", str(duration)]
    
    cmd += ["-ac", "1", "-ar", str(sample_rate), "-f", "wav", output_path]
    return cmd


def _find_ffmpeg() -> Optional[str]:
    env_path = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG_BINARY")
    if env_path and os.path.isfile(env_path):
        return env_path

    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    candidate_dirs: list[str] = []

    # Local project paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_dirs.append(base_dir)
    
    # Check packaging directories
    if sys.platform.startswith("linux"):
        candidate_dirs.append(os.path.join(base_dir, "packaging", "ffmpeg", "linux"))
    elif sys.platform == "darwin":
        candidate_dirs.append(os.path.join(base_dir, "packaging", "ffmpeg", "macos"))
    elif sys.platform == "win32":
        candidate_dirs.append(os.path.join(base_dir, "packaging", "ffmpeg", "windows"))

    if getattr(sys, "frozen", False):
        candidate_dirs.append(os.path.dirname(sys.executable))
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate_dirs.append(meipass)

    for base in candidate_dirs:
        for subdir in ("", "bin", "ffmpeg", "tools"):
            candidate = os.path.join(base, subdir, exe_name)
            if os.path.isfile(candidate):
                # Ensure it's executable on Unix
                if os.name != "nt" and not os.access(candidate, os.X_OK):
                    try:
                        os.chmod(candidate, 0o755)
                    except OSError:
                        pass
                return candidate

    return shutil.which("ffmpeg")


def _run_ffmpeg(cmd: list[str]) -> None:
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(cmd, check=True, startupinfo=startupinfo)
    else:
        subprocess.run(cmd, check=True)


def decode_with_ffmpeg(
    input_path: str,
    sample_rate: int,
    start: Optional[float],
    duration: Optional[float],
) -> str:
    ffmpeg_path = _find_ffmpeg()
    if not ffmpeg_path:
        raise RuntimeError(
            "ffmpeg introuvable. Ajoute ffmpeg a cote de l'executable "
            "ou definis FFMPEG_PATH."
        )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    cmd = build_ffmpeg_cmd(ffmpeg_path, input_path, tmp_path, sample_rate, start, duration)
    try:
        _run_ffmpeg(cmd)
    except subprocess.CalledProcessError as exc:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise RuntimeError("ffmpeg failed to decode the audio file") from exc

    return tmp_path


def estimate_bpm(
    y: np.ndarray, sr: int, hop_length: int, min_bpm: Optional[float], max_bpm: Optional[float]
) -> float:
    """Estimate global BPM using autocorrelation of the onset envelope."""
    # Pro-grade onset strength for stability and accuracy
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length, fmax=8000)
    if onset_env.size == 0:
        raise RuntimeError("Unable to estimate tempo from the audio")

    # Use autocorrelation for superior pulse detection
    # This identifies the global periodicity more robustly than a tempogram argmax
    ac = librosa.autocorrelate(onset_env, max_size=None)
    
    # Range of interesting lags
    # BPM = 60 * sr / (hop_length * lag)
    low = float(min_bpm) if min_bpm is not None else 60.0
    high = float(max_bpm) if max_bpm is not None else 200.0
    
    min_lag = int(60.0 * sr / (hop_length * high))
    max_lag = int(60.0 * sr / (hop_length * low))
    
    if min_lag >= ac.size:
        return float(low)
    max_lag = min(max_lag, ac.size - 1)
    
    # Focus on the peak in the valid range
    search_range = ac[min_lag : max_lag + 1]
    if search_range.size == 0:
        return float(low)
        
    rank = np.argsort(search_range)[::-1]
    best_idx_in_range = rank[0]
    best_idx = best_idx_in_range + min_lag
    
    # Harmonic check: If there's a peak at ~half the lag (double BPM) 
    # that is significant, it's likely the real BPM for electronic music.
    half_lag = best_idx // 2
    if half_lag >= min_lag:
        # Check window around half_lag
        win = 2
        local_max_idx = np.argmax(ac[half_lag-win : half_lag+win+1]) + (half_lag-win)
        if ac[local_max_idx] > ac[best_idx] * 0.6:
            best_idx = local_max_idx

    # Parabolic interpolation on ACF for high precision
    if 0 < best_idx < ac.size - 1:
        y0, y1, y2 = ac[best_idx-1:best_idx+2]
        denom = (y0 - 2*y1 + y2)
        best_lag = best_idx + (0.5 * (y0 - y2) / denom) if abs(denom) > 1e-10 else float(best_idx)
    else:
        best_lag = float(best_idx)
        
    global_bpm = 60.0 * sr / (hop_length * best_lag)
    return global_bpm


def _median_smooth(values: np.ndarray, window_size: int) -> np.ndarray:
    if window_size <= 1:
        return values.copy()
    if window_size % 2 == 0:
        window_size += 1
    half = window_size // 2
    smoothed = np.empty_like(values)
    for i in range(values.size):
        start = max(0, i - half)
        end = min(values.size, i + half + 1)
        smoothed[i] = np.median(values[start:end])
    return smoothed


def _fill_nans(values: np.ndarray) -> np.ndarray:
    if not np.isnan(values).any():
        return values
    valid = ~np.isnan(values)
    if valid.sum() == 0:
        raise RuntimeError("Unable to estimate tempo from silent audio")
    x = np.arange(values.size)
    filled = np.interp(x, x[valid], values[valid])
    return filled


def _beats_to_bpm(
    beat_times: np.ndarray,
    min_bpm: Optional[float],
    max_bpm: Optional[float],
) -> Optional[float]:
    if beat_times.size < 2:
        return None
    intervals = np.diff(beat_times)
    intervals = intervals[intervals > 0]
    if intervals.size == 0:
        return None
    bpm = 60.0 / intervals
    if min_bpm is not None:
        bpm = bpm[bpm >= float(min_bpm)]
    if max_bpm is not None:
        bpm = bpm[bpm <= float(max_bpm)]
    if bpm.size == 0:
        return None
    return float(np.median(bpm))


def _refine_with_beats(
    y: np.ndarray,
    sr: int,
    hop_length: int,
    min_bpm: Optional[float],
    max_bpm: Optional[float],
    start_bpm: float,
) -> tuple[Optional[float], np.ndarray]:
    tempo, beats = librosa.beat.beat_track(
        y=y,
        sr=sr,
        hop_length=hop_length,
        start_bpm=float(start_bpm),
        tightness=400,
    )
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=hop_length)
    refined = _beats_to_bpm(beat_times, min_bpm, max_bpm)
    if refined is None and np.isfinite(tempo):
        refined = float(tempo)
    return refined, beat_times


def _tempo_curve(
    y: np.ndarray,
    sr: int,
    hop_length: int,
    min_bpm: Optional[float],
    max_bpm: Optional[float],
) -> np.ndarray:
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length, fmax=8000)
    if onset_env.size == 0:
        raise RuntimeError("Unable to estimate tempo from the audio")

    tempogram = librosa.feature.tempogram(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
    )
    tempo_bins = librosa.tempo_frequencies(
        tempogram.shape[0], sr=sr, hop_length=hop_length
    )

    if tempogram.shape[0] <= 1:
        raise RuntimeError("Unable to estimate tempo from the audio")

    # Drop lag=0 bin (infinite BPM) to avoid invalid picks.
    tempogram = tempogram[1:, :]
    tempo_bins = tempo_bins[1:]

    if min_bpm is not None or max_bpm is not None:
        low = -np.inf if min_bpm is None else float(min_bpm)
        high = np.inf if max_bpm is None else float(max_bpm)
        if low >= high:
            raise RuntimeError("Invalid BPM range")
        mask = (tempo_bins >= low) & (tempo_bins <= high)
        if np.count_nonzero(mask) < 2:
            raise RuntimeError("BPM range too narrow")
        tempogram = tempogram[mask, :]
        tempo_bins = tempo_bins[mask]

    bpm_curve = tempo_bins[np.argmax(tempogram, axis=0)].astype(float)
    energy_threshold = max(1e-6, 0.1 * float(np.max(onset_env)))
    bpm_curve[onset_env < energy_threshold] = np.nan
    bpm_curve[~np.isfinite(bpm_curve)] = np.nan
    bpm_curve = _fill_nans(bpm_curve)
    return bpm_curve


def _build_segments(
    times: np.ndarray,
    bpm_curve: np.ndarray,
    *,
    change_threshold: float,
    min_segment_duration: float,
    frame_duration: float,
) -> list[dict]:
    segments: list[dict] = []
    if bpm_curve.size == 0:
        return segments

    seg_start = 0
    for i in range(1, bpm_curve.size):
        if abs(bpm_curve[i] - bpm_curve[i - 1]) >= change_threshold:
            end_idx = i - 1
            segment_bpms = bpm_curve[seg_start : end_idx + 1]
            segments.append(
                {
                    "start": float(times[seg_start]),
                    "end": float(times[end_idx] + frame_duration),
                    "bpm": float(np.median(segment_bpms)),
                }
            )
            seg_start = i

    segment_bpms = bpm_curve[seg_start:]
    segments.append(
        {
            "start": float(times[seg_start]),
            "end": float(times[-1] + frame_duration),
            "bpm": float(np.median(segment_bpms)),
        }
    )

    if len(segments) > 1:
        first = segments[0]
        first_duration = first["end"] - first["start"]
        if first_duration < min_segment_duration:
            nxt = segments[1]
            next_duration = nxt["end"] - nxt["start"]
            total = first_duration + next_duration
            if total > 0:
                nxt["bpm"] = (first["bpm"] * first_duration + nxt["bpm"] * next_duration) / total
            nxt["start"] = first["start"]
            segments = segments[1:]

    merged: list[dict] = []
    for seg in segments:
        duration = seg["end"] - seg["start"]
        if not merged:
            merged.append(seg)
            continue
        if duration < min_segment_duration:
            prev = merged[-1]
            prev_duration = prev["end"] - prev["start"]
            total = prev_duration + duration
            if total > 0:
                prev["bpm"] = (prev["bpm"] * prev_duration + seg["bpm"] * duration) / total
            prev["end"] = seg["end"]
        else:
            merged.append(seg)

    return merged


def _merge_similar_segments(
    segments: list[dict], bpm_tolerance: float = 0.75
) -> list[dict]:
    if not segments:
        return segments
    merged: list[dict] = [segments[0].copy()]
    for seg in segments[1:]:
        prev = merged[-1]
        if abs(seg["bpm"] - prev["bpm"]) <= bpm_tolerance:
            prev_duration = prev["end"] - prev["start"]
            seg_duration = seg["end"] - seg["start"]
            total = prev_duration + seg_duration
            if total > 0:
                prev["bpm"] = (prev["bpm"] * prev_duration + seg["bpm"] * seg_duration) / total
            prev["end"] = seg["end"]
        else:
            merged.append(seg.copy())
    return merged


def _snap_value(value: float, *, step: float, tolerance: float) -> float:
    if not np.isfinite(value):
        return value
    if step <= 0:
        return value
    
    # Try snapping to integer first
    # For electronic music, we favor integers heavily.
    # We use a permissive tolerance for integers as most tracks are perfectly quantized.
    # Use a slightly "musical" half-up threshold (0.495) to avoid borderline
    # under-rounding from float noise around x.5 BPM (e.g. 159.495 -> 160).
    floor_v = float(np.floor(value))
    frac = value - floor_v
    snapped_int = int(floor_v + 1.0) if frac >= 0.495 else int(floor_v)
    if abs(value - snapped_int) <= tolerance:
        return float(snapped_int)
    
    # Try snapping to .5
    # Only if it's very close (within 30% of the tolerance)
    snapped_half = round(value * 2) / 2
    if abs(value - snapped_half) <= (tolerance * 0.3):
        return float(snapped_half)

    snapped = round(value / step) * step
    if abs(value - snapped) <= tolerance:
        return float(snapped)
    return value


def detect_bpm_details(
    input_path: str,
    *,
    sample_rate: int = 44100,
    start: Optional[float] = None,
    duration: Optional[float] = None,
    hop_length: int = 96,
    smooth_window: int = 9,
    change_threshold: float = 3.0,
    min_segment_duration: float = 6.0,
    min_bpm: Optional[float] = 60.0,
    max_bpm: Optional[float] = 200.0,
    use_hpss: bool = True,
    snap_bpm: bool = True,
    snap_step: float = 1.0,
    snap_tolerance: float = 0.5,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> dict:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    temp_path = None
    try:
        report = lambda p, s: progress_callback(p, s) if progress_callback else None
        
        try:
            report(10, "Turbo Loading...")
            eff_dur = duration if duration is not None else 60.0
            temp_path = decode_with_ffmpeg(input_path, 22050, start, eff_dur)
            
            report(30, "Fast Load...")
            y, sr = sf.read(temp_path)
            if y.ndim > 1:
                y = np.mean(y, axis=1)
        except RuntimeError:
            report(15, "Load (Fallback)...")
            y, sr = librosa.load(input_path, sr=22050, mono=True, duration=duration or 60.0)

        # Stable resolution: hop=128 at 22k is ~5.8ms precision
        analysis_hop = 128
        
        # Turbo Scan: Directly on v
        report(60, "Scanning...")
        global_bpm = estimate_bpm(y, sr, analysis_hop, min_bpm, max_bpm)
        
        segments = [{"start": 0.0, "end": float(len(y)/sr), "bpm": global_bpm}]

        report(85, "Refining...")
        refined_bpm, beat_times = _refine_with_beats(
            y,
            sr,
            analysis_hop,
            min_bpm,
            max_bpm,
            global_bpm,
        )
        if refined_bpm is not None and np.isfinite(refined_bpm):
            # Hybrid approach: average if they are in the same ballpark
            # This cancels out biases for tracks that are slightly off
            if abs(global_bpm - refined_bpm) < 5.0:
                global_bpm = (global_bpm + refined_bpm) / 2.0
            else:
                # If they differ too much (harmonic error), trust the beat tracking
                global_bpm = refined_bpm

        if segments and beat_times.size >= 2:
            midpoints = (beat_times[:-1] + beat_times[1:]) / 2.0
            beat_bpms = 60.0 / np.diff(beat_times)
            for seg in segments:
                mask = (midpoints >= seg["start"]) & (midpoints < seg["end"])
                if not np.any(mask):
                    continue
                seg_bpms = beat_bpms[mask]
                if min_bpm is not None:
                    seg_bpms = seg_bpms[seg_bpms >= float(min_bpm)]
                if max_bpm is not None:
                    seg_bpms = seg_bpms[seg_bpms <= float(max_bpm)]
                if seg_bpms.size > 0:
                    seg["bpm"] = float(np.median(seg_bpms))

        segments = _merge_similar_segments(segments)

        if snap_bpm:
            # For global BPM, we can be much more aggressive with snapping
            # Permissive for integers (1.1), stricter for .5 (0.3)
            global_bpm = _snap_value(
                global_bpm, step=snap_step, tolerance=max(snap_tolerance, 1.1)
            )
            for seg in segments:
                seg["bpm"] = _snap_value(
                    seg["bpm"], step=snap_step, tolerance=snap_tolerance
                )

        if not np.isfinite(global_bpm):
            raise RuntimeError("Impossible de déterminer le BPM")

        report(100, "Terminé")
        return {
            "bpm": global_bpm,
            "sample_rate": sr,
            "segments": segments,
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def detect_bpm(
    input_path: str,
    *,
    sample_rate: int = 22050,
    start: Optional[float] = None,
    duration: Optional[float] = None,
    min_bpm: Optional[float] = 60.0,
    max_bpm: Optional[float] = 200.0,
) -> tuple[float, int]:
    details = detect_bpm_details(
        input_path,
        sample_rate=sample_rate,
        start=start,
        duration=duration,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
    )
    return details["bpm"], details["sample_rate"]

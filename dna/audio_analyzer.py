"""
dna/audio_analyzer.py

Phase 2: Extracts musical features from audio files using librosa.
Provides BPM, key, mode, structure segmentation, and energy curve.

Prerequisites:
    pip install librosa soundfile numpy
    System: ffmpeg must be installed (brew install ffmpeg / apt install ffmpeg)

CRITICAL: This module operates on audio files you have rights to analyze.
All analysis is transformative — extracts abstract data only (BPM, key, energy).
Delete preview audio immediately after analysis in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print(
        "[WARN] librosa not installed — audio analysis disabled. Run: pip install librosa soundfile"
    )


@dataclass
class AudioAnalysisResult:
    bpm: int
    key: str
    mode: str  # "Major" | "Minor"
    structure: List[str]
    energy_curve: List[float]  # 10-point normalized energy
    duration_s: float
    rms_mean: float = 0.0  # Average loudness proxy


# ─── Key Detection ────────────────────────────────────────────────────────────

_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_MAJOR_TEMPLATE = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1], dtype=float)
_MINOR_TEMPLATE = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0], dtype=float)


def estimate_key(y: "np.ndarray", sr: int) -> Tuple[str, str]:
    """Estimate musical key and mode from chroma features (Krumhansl-Schmuckler)."""
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    major_corrs = [
        np.corrcoef(chroma_mean, np.roll(_MAJOR_TEMPLATE, i))[0, 1] for i in range(12)
    ]
    minor_corrs = [
        np.corrcoef(chroma_mean, np.roll(_MINOR_TEMPLATE, i))[0, 1] for i in range(12)
    ]

    max_major = max(major_corrs)
    max_minor = max(minor_corrs)

    if max_major >= max_minor:
        return _NOTES[int(np.argmax(major_corrs))], "Major"
    return _NOTES[int(np.argmax(minor_corrs))], "Minor"


# ─── Structure Detection ──────────────────────────────────────────────────────


def segment_structure(y: "np.ndarray", sr: int) -> List[str]:
    """
    Energy-heuristic structural segmentation.
    Returns labeled section list. For production, replace with an ML segmenter.
    """
    # Use spectral flux novelty to find change points
    hop_length = 512
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    # Find segment boundaries using recurrence matrix
    try:
        bounds = librosa.segment.agglomerative(oenv, k=min(8, max(3, len(oenv) // 50)))
        num_segments = len(bounds)
    except Exception:
        num_segments = 5  # Fallback

    # Map segment count to plausible structure
    if num_segments <= 3:
        return ["verse", "chorus", "outro"]
    elif num_segments <= 5:
        return ["intro", "verse", "chorus", "verse", "outro"]
    elif num_segments <= 7:
        return ["intro", "verse", "chorus", "verse", "chorus", "bridge", "outro"]
    else:
        return [
            "intro",
            "verse",
            "pre-chorus",
            "chorus",
            "verse",
            "chorus",
            "bridge",
            "chorus",
            "outro",
        ]


# ─── Main Analyzer ────────────────────────────────────────────────────────────


def analyze_audio(audio_path: str) -> Optional[AudioAnalysisResult]:
    """
    Full audio analysis pipeline.
    Loads audio, extracts BPM, key, structure, energy curve.
    Returns None on failure.
    """
    if not LIBROSA_AVAILABLE:
        print("[ERROR] librosa is required for audio analysis")
        return None

    try:
        # Load mono, 22kHz, max 3 minutes (enough for structural analysis)
        y, sr = librosa.load(audio_path, sr=22050, duration=180, mono=True)
    except Exception as e:
        print(f"[ERROR] Could not load audio '{audio_path}': {e}")
        return None

    # BPM
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = int(round(float(tempo)))

    # Key
    key, mode = estimate_key(y, sr)

    # Structure
    structure = segment_structure(y, sr)

    # Energy curve — 10-point normalized RMS
    rms = librosa.feature.rms(y=y)[0]
    rms_min, rms_max = rms.min(), rms.max()
    rms_norm = (rms - rms_min) / (rms_max - rms_min + 1e-8)
    energy_curve = list(
        np.interp(
            np.linspace(0, 1, 10),
            np.linspace(0, 1, len(rms_norm)),
            rms_norm,
        )
    )

    duration = librosa.get_duration(y=y, sr=sr)

    return AudioAnalysisResult(
        bpm=bpm,
        key=key,
        mode=mode,
        structure=structure,
        energy_curve=[round(float(x), 3) for x in energy_curve],
        duration_s=round(duration, 1),
        rms_mean=round(float(rms.mean()), 4),
    )

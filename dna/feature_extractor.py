"""
dna/feature_extractor.py

Phase 2: ML-based audio feature extraction using PANNs
(Pretrained Audio Neural Networks — trained on AudioSet's 527 labels).

Extracts: instrumentation, production style, mood, and genre tags
directly from audio content.

Prerequisites:
    pip install panns-inference torch numpy librosa

Note: First run downloads model weights (~800MB). Subsequent runs are fast.
GPU support: set DEVICE='cuda' if torch.cuda.is_available().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

try:
    import librosa
    import torch
    from panns_inference import AudioTagging

    _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    _MODEL: Optional[AudioTagging] = None  # Lazy-loaded singleton

    def _get_model() -> AudioTagging:
        global _MODEL
        if _MODEL is None:
            print(f"[INFO] Loading PANNs model on {_DEVICE}...")
            _MODEL = AudioTagging(checkpoint_path=None, device=_DEVICE)
        return _MODEL

    PANNS_AVAILABLE = True
except ImportError:
    PANNS_AVAILABLE = False
    print(
        "[WARN] panns-inference / torch not installed — ML feature extraction disabled"
    )


@dataclass
class FeatureExtractionResult:
    instrumentation: List[str] = field(default_factory=list)
    production_tags: List[str] = field(default_factory=list)
    mood_tags: List[str] = field(default_factory=list)
    genre_tags: List[str] = field(default_factory=list)
    raw_scores: dict = field(default_factory=dict)  # label → prob, top 20


# ─── AudioSet Label Classifiers ───────────────────────────────────────────────

_INSTRUMENT_KEYWORDS = [
    "guitar",
    "bass",
    "drum",
    "piano",
    "synthesizer",
    "strings",
    "brass",
    "flute",
    "saxophone",
    "organ",
    "violin",
    "cello",
    "trumpet",
    "electric piano",
    "808",
]
_PRODUCTION_KEYWORDS = [
    "reverb",
    "distortion",
    "lo-fi",
    "echo",
    "choir",
    "harmony",
    "beat",
    "sample",
    "sidechain",
    "delay",
]
_MOOD_KEYWORDS = [
    "mellow",
    "energetic",
    "upbeat",
    "sad",
    "happy",
    "epic",
    "calm",
    "dramatic",
    "funky",
    "aggressive",
    "melancholic",
]
_GENRE_KEYWORDS = [
    "pop",
    "rock",
    "hip hop",
    "jazz",
    "classical",
    "electronic",
    "techno",
    "disco",
    "soul",
    "r&b",
    "reggae",
    "country",
    "folk",
    "house",
    "trap",
    "afrobeats",
]


def _classify_tag(tag: str) -> Tuple[Optional[str], str]:
    """Route a PANNs label to an output category."""
    tag_lower = tag.lower()
    if any(kw in tag_lower for kw in _INSTRUMENT_KEYWORDS):
        return "instrumentation", _normalize_tag(tag)
    if any(kw in tag_lower for kw in _PRODUCTION_KEYWORDS):
        return "production_tags", _normalize_tag(tag)
    if any(kw in tag_lower for kw in _MOOD_KEYWORDS):
        return "mood_tags", _normalize_tag(tag)
    if any(kw in tag_lower for kw in _GENRE_KEYWORDS):
        return "genre_tags", _normalize_tag(tag)
    return None, tag


def _normalize_tag(tag: str) -> str:
    """Normalize a PANNs label to Suno-friendly format."""
    return tag.lower().strip().replace(" ", "_")


# ─── Main Extractor ───────────────────────────────────────────────────────────


def extract_features(
    audio_path: str,
    top_n: int = 15,
) -> FeatureExtractionResult:
    """
    Run PANNs inference on audio file. Returns categorized feature tags.
    Falls back to empty result if PANNs unavailable.
    """
    if not PANNS_AVAILABLE:
        return FeatureExtractionResult()

    try:
        # PANNs expects 32kHz mono numpy array
        audio, _ = librosa.load(audio_path, sr=32000, mono=True, duration=60)
        audio = audio[None, :]  # Add batch dim: (1, T)
    except Exception as e:
        print(f"[ERROR] Could not load audio for ML extraction '{audio_path}': {e}")
        return FeatureExtractionResult()

    model = _get_model()
    with torch.no_grad():
        clipwise_output, _ = model.inference(audio)

    # Get top N labels
    scores = clipwise_output[0]
    top_indices = np.argsort(scores)[::-1][:top_n]
    top_tags = [(model.labels[i], float(scores[i])) for i in top_indices]

    result = FeatureExtractionResult(
        raw_scores={tag: round(prob, 4) for tag, prob in top_tags}
    )

    for tag, _ in top_tags:
        category, normalized = _classify_tag(tag)
        if category:
            bucket: List[str] = getattr(result, category)
            if normalized not in bucket:
                bucket.append(normalized)

    return result

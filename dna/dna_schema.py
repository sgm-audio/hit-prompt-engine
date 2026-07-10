"""
dna/dna_schema.py

Pydantic v2 TrackDNA model — the canonical data structure flowing through
the entire pipeline. Phase 1 fields populate from chart metadata + MusicBrainz.
Phase 2 fields populate from Spotify audio features + deep audio analysis.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class TrackDNA(BaseModel):
    # ── Identity ──────────────────────────────────────────────────────────────
    track_id: str
    title: str
    artist: str  # Internal use only — NEVER injected into Suno prompts
    release_year: int
    genres: List[str] = Field(default_factory=list)
    mbid: Optional[str] = None
    isrc: Optional[str] = None
    spotify_id: Optional[str] = None

    # ── Phase 2: Spotify Extended Features ────────────────────────────────────
    bpm: Optional[float] = None  # Precise tempo (e.g., 118.3)
    key: Optional[str] = None  # e.g., "F# minor"
    mode: Optional[str] = None  # "major" / "minor"
    energy: Optional[float] = None  # 0.0–1.0
    valence: Optional[float] = None  # Mood: sad (0.0) → happy (1.0)
    danceability: Optional[float] = None  # 0.0–1.0
    acousticness: Optional[float] = None  # 0.0–1.0
    instrumentalness: Optional[float] = None

    # ── Phase 2: Deep Audio Analysis (from preview) ───────────────────────────
    structure: List[str] = Field(
        default_factory=lambda: [
            "intro",
            "verse",
            "chorus",
            "verse",
            "chorus",
            "bridge",
            "chorus",
            "outro",
        ]
    )
    energy_curve: Dict[str, float] = Field(
        default_factory=dict
    )  # section → energy level
    instrumentation: List[str] = Field(
        default_factory=list
    )  # e.g., ["808", "funky_bass", "synth_pad"]
    production_tags: List[str] = Field(
        default_factory=list
    )  # e.g., ["gated_reverb", "sidechain"]
    vocal_profile: Optional[str] = (
        None  # "male_lead", "female_harmony", "rap", "layered"
    )

    # ── Safe Inference ────────────────────────────────────────────────────────
    lyric_themes: List[str] = Field(
        default_factory=list
    )  # ["confidence", "heartbreak", "nightlife"]
    uniqueness_hooks: List[str] = Field(
        default_factory=list
    )  # ["iconic_bassline_feel", "syncopated_rhythm"]

    # ── Pipeline Metadata ─────────────────────────────────────────────────────
    analysis_version: str = "2.0"
    preview_analyzed: bool = False

    # ── Computed Helpers ──────────────────────────────────────────────────────

    def energy_label(self) -> str:
        """Convert 0.0–1.0 energy float to Suno-useful label."""
        if self.energy is None:
            return "mid"
        if self.energy >= 0.8:
            return "peak"
        elif self.energy >= 0.6:
            return "high"
        elif self.energy >= 0.35:
            return "mid"
        return "low"

    def bpm_int(self) -> Optional[int]:
        return int(round(self.bpm)) if self.bpm else None

    def era(self) -> str:
        """Return decade-era string from release year."""
        y = self.release_year
        if y < 1980:
            return "1970s"
        elif y < 1990:
            return "1980s"
        elif y < 2000:
            return "1990s"
        elif y < 2010:
            return "2000s"
        elif y < 2020:
            return "2010s"
        elif y < 2024:
            return "2020s"
        return "2026"

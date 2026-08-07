"""
dna/dna_schema.py

Pydantic v2 TrackDNA model — the canonical data structure flowing through
the entire pipeline. Phase 1 fields populate from chart metadata + MusicBrainz.
Phase 2 fields populate from Spotify audio features + deep audio analysis.
"""


from pydantic import BaseModel, Field


class TrackDNA(BaseModel):
    # ── Identity ──────────────────────────────────────────────────────────────
    track_id: str
    title: str
    artist: str  # Internal use only — NEVER injected into Suno prompts
    release_year: int
    genres: list[str] = Field(default_factory=list)
    mbid: str | None = None
    isrc: str | None = None
    spotify_id: str | None = None

    # ── Phase 2: Spotify Extended Features ────────────────────────────────────
    bpm: float | None = None  # Precise tempo (e.g., 118.3)
    key: str | None = None  # e.g., "F# minor"
    mode: str | None = None  # "major" / "minor"
    energy: float | None = None  # 0.0–1.0
    valence: float | None = None  # Mood: sad (0.0) → happy (1.0)
    danceability: float | None = None  # 0.0–1.0
    acousticness: float | None = None  # 0.0–1.0
    instrumentalness: float | None = None

    # ── Phase 2: Deep Audio Analysis (from preview) ───────────────────────────
    structure: list[str] = Field(
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
    energy_curve: dict[str, float] = Field(
        default_factory=dict
    )  # section → energy level
    instrumentation: list[str] = Field(
        default_factory=list
    )  # e.g., ["808", "funky_bass", "synth_pad"]
    production_tags: list[str] = Field(
        default_factory=list
    )  # e.g., ["gated_reverb", "sidechain"]
    vocal_profile: str | None = (
        None  # "male_lead", "female_harmony", "rap", "layered"
    )

    # ── Safe Inference ────────────────────────────────────────────────────────
    lyric_themes: list[str] = Field(
        default_factory=list
    )  # ["confidence", "heartbreak", "nightlife"]
    uniqueness_hooks: list[str] = Field(
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

    def bpm_int(self) -> int | None:
        return round(self.bpm) if self.bpm else None

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

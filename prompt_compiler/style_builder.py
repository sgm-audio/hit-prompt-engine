"""
prompt_compiler/style_builder.py

Builds Suno-optimized Style field strings (max 200 chars).

Tag order (Suno weighs start of field most):
  Genre → BPM → Era/Texture → Energy → Instrumentation → Vocals → Production

NEVER injects artist names, song titles, or any copyrightable content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from dna.dna_schema import TrackDNA

import random

STYLE_CHAR_LIMIT = 200

# ─── Era → Production Descriptor ─────────────────────────────────────────────

ERA_PRODUCTION_MAP: dict[str, str] = {
    "1970s": "analog warmth, tape saturation, wide stereo, live room feel",
    "1980s": "gated reverb drums, bright synth stabs, DX7 bass, glossy mix",
    "1990s": "90s boom-bap, clean low end, sampled drums, cassette warmth",
    "2000s": "polished radio mix, compressed punch, pop rock energy",
    "2010s": "EDM influence, sidechain pump, trap hi-hats, crisp 808",
    "2020s": "modern trap, cloud rap atmosphere, drill rhythm, hyperpop edge",
    "2026": "neo-soul blend, bedroom pop warmth, lo-fi clarity, spatial audio",
}

# ─── Genre Tag Map ────────────────────────────────────────────────────────────

GENRE_TAG_MAP: dict[str, str] = {
    "pop": "pop",
    "hip_hop": "hip-hop",
    "rnb": "R&B soul",
    "country": "country",
    "rock": "rock",
    "alternative": "alternative rock",
    "electronic": "electronic dance",
    "latin": "latin pop",
    "dance": "dance pop",
    "gospel": "gospel",
    "reggae": "reggae",
    "kpop": "K-pop",
    "afrobeats": "afrobeats",
    "metal": "heavy metal",
    "jazz": "jazz",
    "folk": "folk acoustic",
    "blues": "blues",
    "funk": "funk groove",
    "punk": "punk rock",
    "classical": "orchestral",
}

# ─── Energy → Mood Descriptor ─────────────────────────────────────────────────

ENERGY_MAP: dict[str, str] = {
    "low": "mellow, intimate",
    "mid": "moderate energy, steady groove",
    "high": "high energy, driving rhythm",
    "peak": "peak energy, euphoric, anthemic",
}

# ─── Vocal Profile Map ────────────────────────────────────────────────────────

VOCAL_MAP: dict[str, str] = {
    "male_pop": "polished male vocals",
    "male_rock": "raw male rock vocals",
    "female_pop": "bright female vocals",
    "female_rnb": "soulful female vocals",
    "rap_male": "male rap delivery",
    "rap_female": "female rap vocals",
    "choir": "layered vocal harmonies",
    "layered": "stacked vocal harmonies",
}


# ─── Main Style Builder ───────────────────────────────────────────────────────


def build_style_prompt(dna: "TrackDNA", variation: str = "faithful") -> str:
    """
    Builds a Suno-optimized Style field (max 200 chars).
    Never includes artist names or song titles.
    """
    era = dna.era()
    era_prod = ERA_PRODUCTION_MAP.get(era, "")
    bpm = dna.bpm_int()
    energy_label = dna.energy_label()

    # Primary genre (Suno weights start of field most)
    primary_genre_key = dna.genres[0].lower() if dna.genres else "pop"
    primary_genre = GENRE_TAG_MAP.get(primary_genre_key, primary_genre_key)

    # Build parts list
    parts: List[str] = []

    if variation == "faithful":
        parts.append(primary_genre)
        if bpm:
            parts.append(f"{bpm} BPM")
        parts.append(ENERGY_MAP.get(energy_label, "dynamic"))
        if dna.key:
            parts.append(dna.key)
        if dna.instrumentation:
            parts.extend(dna.instrumentation[:2])
        if dna.vocal_profile:
            parts.append(VOCAL_MAP.get(dna.vocal_profile, dna.vocal_profile))
        if era_prod:
            parts.append(era_prod.split(",")[0].strip())
        if dna.production_tags:
            parts.extend(dna.production_tags[:1])

    elif variation == "modern_2026":
        parts = [primary_genre, "2026 production"]
        if bpm:
            parts.append(f"{bpm} BPM")
        parts += [
            ENERGY_MAP.get(energy_label, "dynamic"),
            "modern mix",
            "streaming-ready",
        ]
        if dna.instrumentation:
            parts.extend(dna.instrumentation[:2])

    elif variation == "genre_bent":
        alt_keys = [k for k in GENRE_TAG_MAP if k not in dna.genres]
        bent_key = random.choice(alt_keys[:8])
        bent_genre = GENRE_TAG_MAP[bent_key]
        parts = [
            f"{primary_genre}-influenced {bent_genre}",
            f"{bpm} BPM" if bpm else "groove-driven",
            ENERGY_MAP.get(energy_label, "dynamic"),
        ]
        if dna.instrumentation:
            parts.extend(dna.instrumentation[:2])

    elif variation == "stripped":
        parts = [
            f"acoustic {primary_genre}",
            "stripped down",
            "intimate",
            "minimal arrangement",
        ]
        if dna.vocal_profile:
            parts.append(VOCAL_MAP.get(dna.vocal_profile, "lead vocals"))
        if bpm and bpm > 80:
            stripped_bpm = max(60, bpm - 8)
            parts.append(f"{stripped_bpm} BPM")

    elif variation == "instrumental":
        parts = [
            primary_genre,
            f"{bpm} BPM" if bpm else "",
            era_prod.split(",")[0].strip() if era_prod else "",
            "instrumental",
            "no vocals",
            "sync-ready",
        ]
        if dna.instrumentation:
            parts.extend(dna.instrumentation[:2])

    elif variation == "club_remix":
        club_bpm = min(160, (bpm or 120) + 10)
        parts = [
            primary_genre,
            "club remix",
            f"{club_bpm} BPM",
            "four-on-the-floor",
            "extended intro",
            "DJ mix",
            "peak energy",
            "festival drop",
        ]

    # Clean and enforce char limit
    style = ", ".join(p for p in parts if p and p.strip())
    while len(style) > STYLE_CHAR_LIMIT and "," in style:
        style = style.rsplit(",", 1)[0]

    return style.strip(", ")

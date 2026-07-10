"""
prompt_compiler/variation_engine.py

Generates all 6 variation prompt packs per track.
Each variation targets a different creative direction while staying
rights-safe (no artist names, no lyric copying, only sonic DNA).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List

from prompt_compiler.style_builder import build_style_prompt
from prompt_compiler.lyrics_builder import build_lyrics_block

if TYPE_CHECKING:
    from dna.dna_schema import TrackDNA


VARIATION_RECIPES: List[Dict] = [
    {
        "id": "V1_faithful",
        "name": "Faithful Essence",
        "intent": "Closest to the original feel, fully original composition",
        "style_mod": "faithful",
        "lyrics_mod": "faithful",
        "instrumental": False,
        "bpm_delta": 0,
    },
    {
        "id": "V2_modern_2026",
        "name": "Modern Radio 2026",
        "intent": "Updated mix, contemporary drum palette, streaming-ready",
        "style_mod": "modern_2026",
        "lyrics_mod": "modern_2026",
        "instrumental": False,
        "bpm_delta": 2,
    },
    {
        "id": "V3_genre_bent",
        "name": "Genre-Bent",
        "intent": "Cross-genre surprise — same emotional arc, different sonic world",
        "style_mod": "genre_bent",
        "lyrics_mod": "faithful",
        "instrumental": False,
        "bpm_delta": 0,
    },
    {
        "id": "V4_stripped",
        "name": "Stripped Acoustic",
        "intent": "Minimal, intimate, acoustic-leaning version",
        "style_mod": "stripped",
        "lyrics_mod": "stripped",
        "instrumental": False,
        "bpm_delta": -8,
    },
    {
        "id": "V5_instrumental",
        "name": "Instrumental Sync",
        "intent": "Clean instrumental for sync licensing / creators",
        "style_mod": "instrumental",
        "lyrics_mod": "instrumental",
        "instrumental": True,
        "bpm_delta": 0,
    },
    {
        "id": "V6_club_remix",
        "name": "Club Remix",
        "intent": "Extended build/drop, DJ-friendly, peak energy",
        "style_mod": "club_remix",
        "lyrics_mod": "club_remix",
        "instrumental": False,
        "bpm_delta": 10,
    },
]


@dataclass
class PromptPack:
    track_id: str
    variation_id: str
    variation_name: str
    intent: str
    style: str
    lyrics: str
    instrumental: bool
    settings: Dict = field(default_factory=dict)
    lint: Dict = field(default_factory=dict)


def generate_prompt_pack(dna: "TrackDNA") -> List[PromptPack]:
    """Generate all 6 variation packs for a TrackDNA."""
    packs: List[PromptPack] = []

    for recipe in VARIATION_RECIPES:
        # Apply BPM delta to a copy of the DNA
        modified_dna = copy.copy(dna)
        if recipe["bpm_delta"] != 0 and dna.bpm:
            modified_dna.bpm = max(60.0, (dna.bpm or 120.0) + recipe["bpm_delta"])

        style = build_style_prompt(modified_dna, variation=recipe["style_mod"])
        lyrics = build_lyrics_block(modified_dna, variation=recipe["lyrics_mod"])

        pack = PromptPack(
            track_id=dna.track_id,
            variation_id=recipe["id"],
            variation_name=recipe["name"],
            intent=recipe["intent"],
            style=style,
            lyrics=lyrics,
            instrumental=recipe["instrumental"],
            settings={
                "bpm": modified_dna.bpm_int(),
                "key": dna.key,
                "vocal_profile": dna.vocal_profile
                if not recipe["instrumental"]
                else None,
            },
        )
        packs.append(pack)

    return packs


def export_prompt_pack_json(dna: "TrackDNA") -> dict:
    """Export all 6 variations as a clean JSON-serializable dict."""
    packs = generate_prompt_pack(dna)
    return {
        "track_id": dna.track_id,
        "source_title": dna.title,
        "source_artist": dna.artist,
        "source_year": dna.release_year,
        "primary_genre": dna.genres[0] if dna.genres else "pop",
        "analysis_version": dna.analysis_version,
        "variations": [
            {
                "id": p.variation_id,
                "name": p.variation_name,
                "intent": p.intent,
                "suno_style": p.style,
                "suno_lyrics": p.lyrics,
                "instrumental": p.instrumental,
                "settings": p.settings,
                "lint": p.lint,
            }
            for p in packs
        ],
    }

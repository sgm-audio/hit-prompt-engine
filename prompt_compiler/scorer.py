"""
prompt_compiler/scorer.py

Auto-scoring engine for generated Suno prompt packs.
Compares generated output against a target blueprint to produce a
quantitative quality score (0–100) with per-dimension breakdowns.

Scoring dimensions (Pat Pattison-informed prosody + Suno-specific heuristics):
  1. Structure Adherence  (40 pts) — did it hit the requested sections?
  2. Tempo Accuracy       (20 pts) — BPM delta from target
  3. Prosody Quality      (20 pts) — rhyme density, line balance, hook strength
  4. Style Field Quality  (10 pts) — lint score pass-through
  5. Thematic Coherence   (10 pts) — theme consistency across variations

References:
  - Pat Pattison, "Songwriting: Essential Guide to Rhyme" (chaps 3, 5):
    mapped rhyme scheme density → emotional resonance index
  - Suno prompt engineering findings: style field tag ordering, char limits
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from prompt_compiler.prompt_linter import lint_prompt

if TYPE_CHECKING:
    from prompt_compiler.variation_engine import PromptPack
    from dna.dna_schema import TrackDNA


# ─── Score Result ─────────────────────────────────────────────────────────────


@dataclass
class ScoreResult:
    total: int  # 0–100
    grade: str  # A / B / C / D / F
    dimensions: Dict[str, int]  # per-dimension scores
    flags: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "grade": self.grade,
            "dimensions": self.dimensions,
            "flags": self.flags,
            "suggestions": self.suggestions,
        }


# ─── Scoring Dimensions ───────────────────────────────────────────────────────

# Standard Suno section vocabulary
SECTION_TAGS = {
    "verse",
    "chorus",
    "bridge",
    "hook",
    "intro",
    "outro",
    "drop",
    "break",
    "pre-chorus",
    "rap verse",
    "spoken word",
}

# Rhyme-dense keywords that signal prosodic intentionality (Pattison ch.5)
RHYME_INDICATORS = [
    "rhyme",
    "hook",
    "singable",
    "melody",
    "repeat",
    "stack",
    "harmonies",
]


def _score_structure(pack: "PromptPack", target_structure: List[str]) -> int:
    """
    40 pts: Did the generated lyrics include all requested sections?
    Deduct 5 pts per missing section (max 40).
    """
    lyrics_lower = pack.lyrics.lower()
    present = sum(
        1
        for section in target_structure
        if f"[{section}" in lyrics_lower or section.lower() in lyrics_lower
    )
    if not target_structure:
        return 40
    ratio = present / len(target_structure)
    return min(40, int(ratio * 40))


def _score_tempo(detected_bpm: Optional[int], target_bpm: Optional[int]) -> int:
    """
    20 pts: BPM accuracy.
    0 diff → 20, ±5 → 15, ±10 → 10, ±15 → 5, >15 → 0.
    If no BPM available → 10 (neutral).
    """
    if detected_bpm is None or target_bpm is None:
        return 10
    diff = abs(detected_bpm - target_bpm)
    if diff <= 2:
        return 20
    if diff <= 5:
        return 17
    if diff <= 10:
        return 12
    if diff <= 15:
        return 7
    return 3


def _score_prosody(lyrics: str) -> int:
    """
    20 pts: Heuristic prosody quality based on Pat Pattison's rhyme-emotion mapping.
    Checks: producer cue density, line balance, hook presence, section variety.
    """
    score = 0

    # 1. Producer cues present (5 pts) — signals intentional direction
    cue_count = len(re.findall(r"\(.*?\)", lyrics))
    score += min(5, cue_count)

    # 2. Section variety (5 pts) — multiple different sections signal structure
    sections_found = {tag for tag in SECTION_TAGS if f"[{tag}" in lyrics.lower()}
    score += min(5, len(sections_found))

    # 3. Hook presence (5 pts) — Pattison: hook is the emotional peak
    has_hook = any(kw in lyrics.lower() for kw in RHYME_INDICATORS)
    if has_hook:
        score += 5

    # 4. Line balance (5 pts) — even line lengths suggest singable cadence
    non_tag_lines = [
        line.strip()
        for line in lyrics.split("\n")
        if line.strip()
        and not line.strip().startswith("[")
        and not line.strip().startswith("(")
    ]
    if non_tag_lines:
        lengths = [len(line) for line in non_tag_lines]
        # Ideal singable line: 20–60 chars (Pattison ch.3)
        in_range = sum(1 for length in lengths if 10 <= length <= 80)
        balance_ratio = in_range / len(lengths)
        score += int(balance_ratio * 5)

    return min(20, score)


def _score_style_quality(pack: "PromptPack") -> int:
    """10 pts: Pass-through from prompt linter score."""
    result = lint_prompt(pack.style, pack.lyrics, instrumental=pack.instrumental)
    return int(result.score * 10)


def _score_thematic_coherence(packs: List["PromptPack"], dna: "TrackDNA") -> int:
    """
    10 pts: Do all variations reference the same thematic territory?
    Check theme keywords appear consistently across lyrics.
    """
    if not dna.lyric_themes:
        return 5  # Neutral — no target themes to check against

    theme_hits = 0
    for pack in packs:
        if pack.instrumental:
            continue
        lyrics_lower = pack.lyrics.lower()
        # Check if any theme seed appears in the lyrics direction
        for theme in dna.lyric_themes[:2]:
            if theme in lyrics_lower:
                theme_hits += 1

    non_instrumental = len([p for p in packs if not p.instrumental])
    if non_instrumental == 0:
        return 10

    ratio = theme_hits / (non_instrumental * 2)
    return min(10, int(ratio * 10))


def _letter_grade(total: int) -> str:
    if total >= 90:
        return "A"
    if total >= 80:
        return "B"
    if total >= 70:
        return "C"
    if total >= 60:
        return "D"
    return "F"


# ─── Public API ───────────────────────────────────────────────────────────────


def score_pack(
    pack: "PromptPack",
    dna: "TrackDNA",
    all_packs: Optional[List["PromptPack"]] = None,
) -> ScoreResult:
    """
    Score a single PromptPack against its source TrackDNA blueprint.

    Args:
        pack:      The PromptPack to score
        dna:       Source TrackDNA (target blueprint)
        all_packs: Full 6-pack list for thematic coherence check

    Returns:
        ScoreResult with total (0–100), grade, and per-dimension breakdown
    """
    target_bpm = dna.bpm_int()
    detected_bpm = pack.settings.get("bpm")

    dim_structure = _score_structure(pack, dna.structure)
    dim_tempo = _score_tempo(detected_bpm, target_bpm)
    dim_prosody = _score_prosody(pack.lyrics)
    dim_style = _score_style_quality(pack)
    dim_theme = _score_thematic_coherence(all_packs or [pack], dna)

    total = dim_structure + dim_tempo + dim_prosody + dim_style + dim_theme

    flags: List[str] = []
    suggestions: List[str] = []

    if dim_structure < 24:
        flags.append("Missing key structural sections")
        suggestions.append("Ensure all required [Section] tags are present in lyrics")

    if dim_tempo < 10 and target_bpm:
        flags.append(f"BPM mismatch — target {target_bpm}, got {detected_bpm}")
        suggestions.append("Verify BPM appears in style field")

    if dim_prosody < 10:
        flags.append("Low prosody signal — lyrics lack structural direction")
        suggestions.append("Add producer cues (parentheses) and hook direction")

    if dim_style < 6:
        flags.append("Style field quality low — check lint errors")

    return ScoreResult(
        total=min(100, total),
        grade=_letter_grade(min(100, total)),
        dimensions={
            "structure_adherence": dim_structure,
            "tempo_accuracy": dim_tempo,
            "prosody_quality": dim_prosody,
            "style_field_quality": dim_style,
            "thematic_coherence": dim_theme,
        },
        flags=flags,
        suggestions=suggestions,
    )


def score_all_packs(
    packs: List["PromptPack"], dna: "TrackDNA"
) -> Dict[str, ScoreResult]:
    """Score all 6 variations. Returns {variation_id: ScoreResult}."""
    return {pack.variation_id: score_pack(pack, dna, all_packs=packs) for pack in packs}

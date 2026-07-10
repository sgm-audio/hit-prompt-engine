"""
prompt_compiler/prompt_linter.py

Quality gate for generated Suno prompts.
Checks style fields and lyrics blocks for common issues:
  - Char limit violations
  - Artist name injection (copyright risk)
  - Missing structure tags
  - BPM/genre ordering
  - Known problematic lyric fragments

Returns a LintResult with score (0.0–1.0), warnings, errors, suggestions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# ─── Block Lists ──────────────────────────────────────────────────────────────

BLOCKED_ARTIST_TERMS: List[str] = [
    "taylor swift",
    "beyonce",
    "beyoncé",
    "drake",
    "michael jackson",
    "beatles",
    "rolling stones",
    "elvis",
    "eminem",
    "rihanna",
    "madonna",
    "prince",
    "led zeppelin",
    "kendrick lamar",
    "frank ocean",
    "bad bunny",
    "the weeknd",
    "billie eilish",
    "adele",
    "ed sheeran",
    "ariana grande",
]

# Known iconic lyric fragments to block (seed list — expand over time)
BLOCKED_LYRIC_FRAGMENTS: List[str] = [
    "i will always love you",
    "thriller thriller night",
    "billie jean is not my lover",
    "baby one more time",
    "i want it that way",
    "every breath you take",
    "smells like teen spirit",
]

# Suno style field hard limit
STYLE_CHAR_LIMIT = 200

# Ideal range
STYLE_MIN_TAGS = 4
STYLE_MAX_TAGS = 12

# Common genres that should appear early in style field
KNOWN_GENRES = [
    "pop",
    "hip-hop",
    "rock",
    "r&b",
    "country",
    "electronic",
    "dance",
    "latin",
    "reggae",
    "afrobeats",
    "k-pop",
    "gospel",
    "jazz",
    "folk",
    "funk",
    "soul",
    "metal",
    "punk",
    "alternative",
    "orchestral",
    "blues",
    "classical",
]


# ─── Result Type ──────────────────────────────────────────────────────────────


@dataclass
class LintResult:
    passed: bool
    score: float  # 0.0 – 1.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "warnings": self.warnings,
            "errors": self.errors,
            "suggestions": self.suggestions,
        }


# ─── Main Linter ──────────────────────────────────────────────────────────────


def lint_prompt(
    style: str,
    lyrics: str,
    instrumental: bool = False,
) -> LintResult:
    """
    Validate a Suno style + lyrics pair.
    Returns LintResult with pass/fail, score, and actionable feedback.
    """
    warnings: List[str] = []
    errors: List[str] = []
    suggestions: List[str] = []

    style_lower = style.lower()
    lyrics_lower = lyrics.lower()

    # ── STYLE FIELD ──────────────────────────────────────────────────────────

    # 1. Char limit
    if len(style) > STYLE_CHAR_LIMIT:
        errors.append(
            f"Style too long: {len(style)}/{STYLE_CHAR_LIMIT} chars. Trim: '…{style[-20:]}'"
        )
    elif len(style) > STYLE_CHAR_LIMIT - 20:
        warnings.append(f"Style near limit: {len(style)}/{STYLE_CHAR_LIMIT} chars")

    # 2. Artist name injection
    for blocked in BLOCKED_ARTIST_TERMS:
        if blocked in style_lower:
            errors.append(
                f"Style contains artist name '{blocked}' — copyright risk. Remove it."
            )

    # 3. Genre should lead
    first_tag = style_lower.split(",")[0].strip()
    if not any(g in first_tag for g in KNOWN_GENRES):
        warnings.append(f"Style doesn't start with a clear genre: '{first_tag}'")
        suggestions.append(
            "Put primary genre as first tag — Suno weights the start of the field most."
        )

    # 4. BPM specificity
    if not re.search(r"\d+\s*bpm", style_lower):
        suggestions.append(
            "Add specific BPM (e.g., '118 BPM') for better tempo control."
        )

    # 5. Tag count
    tags = [t for t in style.split(",") if t.strip()]
    if len(tags) < STYLE_MIN_TAGS:
        warnings.append(
            f"Only {len(tags)} style tags — recommend {STYLE_MIN_TAGS}–{STYLE_MAX_TAGS} for best results."
        )
    elif len(tags) > STYLE_MAX_TAGS:
        warnings.append(
            f"{len(tags)} style tags may introduce noise — trim to {STYLE_MAX_TAGS}."
        )

    # ── LYRICS FIELD ─────────────────────────────────────────────────────────

    if not instrumental:
        # 6. Must have at least one section tag
        if not re.search(
            r"\[(verse|chorus|bridge|hook|intro|outro|drop|break)", lyrics_lower
        ):
            errors.append(
                "Lyrics must contain at least one section tag: [Verse], [Chorus], etc."
            )

        # 7. Artist name check in lyrics
        for blocked in BLOCKED_ARTIST_TERMS:
            if blocked in lyrics_lower:
                errors.append(f"Lyrics reference artist name '{blocked}' — remove it.")

        # 8. Iconic lyric fragment check
        for fragment in BLOCKED_LYRIC_FRAGMENTS:
            if fragment in lyrics_lower:
                errors.append(
                    f"Possible copyrighted lyric detected: '{fragment}' — rewrite."
                )

        # 9. Lyrics length
        if len(lyrics) > 3000:
            errors.append(f"Lyrics too long: {len(lyrics)} chars (Suno max ~3000).")

        # 10. Empty sections
        sections = re.split(r"\[.*?\]", lyrics)
        empty = sum(1 for s in sections if not s.strip())
        if empty > 2:
            warnings.append(
                f"{empty} section blocks appear empty — add creative direction."
            )

    # ── SCORE ─────────────────────────────────────────────────────────────────

    error_penalty = len(errors) * 0.25
    warning_penalty = len(warnings) * 0.08
    score = max(0.0, 1.0 - error_penalty - warning_penalty)
    passed = len(errors) == 0 and score >= 0.6

    return LintResult(
        passed=passed,
        score=round(score, 2),
        warnings=warnings,
        errors=errors,
        suggestions=suggestions,
    )

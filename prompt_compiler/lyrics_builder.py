"""
prompt_compiler/lyrics_builder.py

Builds structured original lyric scaffolds for Suno Custom Mode.
These are ORIGINAL creative direction blocks — NOT copies or derivatives
of any real song lyrics. They provide structural and thematic guidance only.

Suno interprets [Section] tags structurally.
Producer cues in (parentheses) guide delivery and feel.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from dna.dna_schema import TrackDNA

# ─── Section Tags ─────────────────────────────────────────────────────────────

SECTION_TAG_MAP: dict[str, str] = {
    "intro": "[Intro]",
    "verse": "[Verse]",
    "pre-chorus": "[Pre-Chorus]",
    "pre_chorus": "[Pre-Chorus]",
    "chorus": "[Chorus]",
    "bridge": "[Bridge]",
    "breakdown": "[Break]",
    "drop": "[Drop]",
    "outro": "[Outro]",
    "hook": "[Hook]",
    "solo": "[Guitar Solo]",
    "rap": "[Rap Verse]",
    "spoken": "[Spoken Word]",
}

# ─── Theme → Creative Direction Seeds ────────────────────────────────────────

THEME_SEEDS: dict[str, list[str]] = {
    "confidence": [
        "power in the room, unshakeable presence",
        "owning every step, eyes on the horizon",
    ],
    "romance": ["gravity pulling us together", "couldn't hide it if I tried"],
    "heartbreak": ["empty spaces where you used to be", "echoes of what we had"],
    "nightlife": [
        "city lights at 2am, pulse of the bassline",
        "lost in the crowd, found in the beat",
    ],
    "triumph": [
        "rose from the ashes, they never saw this coming",
        "started with nothing, built it all",
    ],
    "nostalgia": [
        "summers we can't go back to, voices in the wind",
        "faded but never forgotten",
    ],
    "rebellion": ["breaking every rule they wrote for us", "wild hearts don't follow"],
    "hustle": [
        "grind never stops, eyes on everything",
        "brick by brick, building the dream",
    ],
    "spirituality": [
        "something bigger than this moment",
        "grace finding me when I needed it most",
    ],
    "journey": ["miles between here and who I was", "road wide open, horizon calling"],
    "tension": [
        "pressure building to the breaking point",
        "the silence before the storm",
    ],
    "energy": ["electric current through the room", "ignite, don't hold back"],
    "euphoria": ["weightless at the peak of it", "pure feeling, no words needed"],
    "emotion": ["raw and real, nothing left to hide", "every note carries the weight"],
    "storytelling": ["chapter one of something real", "the truth dressed up in melody"],
}

# ─── Delivery Cue by Variation ────────────────────────────────────────────────

DELIVERY_CUES: dict[str, str] = {
    "faithful": "natural flow, match the era feel, authentic delivery",
    "modern_2026": "modern cadence, viral hook potential, short punchy lines",
    "stripped": "soft, confessional delivery — close-mic intimacy, every word counts",
    "club_remix": "punchy hooks, crowd-ready, repeat the hook 2x, ad-libs on the 2 and 4",
    "genre_bent": "unexpected phrasing, embrace the genre shift, surprise the listener",
    "instrumental": "(no lyrics needed — pure musical storytelling)",
}


# ─── Main Builder ─────────────────────────────────────────────────────────────


def build_lyrics_block(dna: "TrackDNA", variation: str = "faithful") -> str:
    """
    Builds a structured lyric scaffold for Suno Custom Mode.
    - Uses [Section] tags for structural control
    - Uses producer cues (in parentheses) for feel direction
    - ORIGINAL thematic direction only — no real lyrics copied
    """
    if variation == "instrumental":
        return "(Instrumental — no lyrics)"

    structure = dna.structure or [
        "intro",
        "verse",
        "chorus",
        "verse",
        "chorus",
        "bridge",
        "chorus",
        "outro",
    ]
    delivery_cue = DELIVERY_CUES.get(variation, DELIVERY_CUES["faithful"])

    # Gather theme seeds
    themes = dna.lyric_themes or ["emotion", "storytelling"]
    seed_lines: List[str] = []
    for theme in themes[:2]:
        seeds = THEME_SEEDS.get(theme, ["raw emotion, vivid imagery"])
        seed_lines.extend(seeds[:1])

    theme_direction = (
        " / ".join(seed_lines) if seed_lines else "raw emotion, vivid imagery"
    )
    hook_line = seed_lines[-1] if seed_lines else "the emotional peak of the song"

    # Build block
    lines: List[str] = [
        f"(Theme direction: {theme_direction})",
        f"(Delivery: {delivery_cue})",
        "",
    ]

    chorus_count = 0
    for section in structure:
        tag = SECTION_TAG_MAP.get(section.lower(), f"[{section.title()}]")
        lines.append(tag)

        s = section.lower().replace("-", "_")
        if s == "intro":
            lines.append(
                "(instrumental, 4-8 bars, let the vibe breathe before the first word)"
            )
        elif s == "verse":
            lines.append(
                f"(story setup: {seed_lines[0] if seed_lines else 'emotional truth'})"
            )
            lines.append(
                "(4 lines, conversational pace, build tension toward the hook)"
            )
        elif s in ("pre_chorus", "pre-chorus"):
            lines.append("(2 lines, lift the energy, make the hook feel inevitable)")
        elif s == "chorus":
            chorus_count += 1
            if chorus_count == 1:
                lines.append(f"(MAIN HOOK: {hook_line})")
                lines.append(
                    "(4 lines, big singable melody, stack harmonies on the repeat)"
                )
            else:
                lines.append(
                    "(repeat hook — add ad-libs on phrases, swell the production)"
                )
        elif s == "bridge":
            lines.append("(shift perspective — half-time feel or key change)")
            lines.append(
                "(4 lines, unexpected emotional turn, bring resolution or revelation)"
            )
        elif s in ("drop", "breakdown"):
            lines.append(
                "(instrumental break, 8 bars, let the production carry the emotion)"
            )
        elif s == "outro":
            lines.append(
                "(fade out or cold stop — bring it home, leave them with the hook)"
            )
        elif s == "hook":
            lines.append(f"(HOOK: {hook_line} — singable, 2-4 lines, repeatable)")

        lines.append("")  # Blank line between sections

    return "\n".join(lines).strip()

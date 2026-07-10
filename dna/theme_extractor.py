"""
dna/theme_extractor.py

Safe theme inference from track metadata only.
NEVER reads, processes, or references actual song lyrics.
All inference is from: title keywords, genre, and acoustic features (valence, energy).
"""

from typing import List, Optional

# ─── Title keyword → theme seeds ─────────────────────────────────────────────

_TITLE_RULES: list[tuple[list[str], str]] = [
    (["love", "heart", "baby", "girl", "boy", "darling", "honey"], "romance"),
    (["night", "club", "party", "dance", "floor", "lights"], "nightlife"),
    (["sad", "cry", "tears", "broken", "hurt", "gone", "alone"], "heartbreak"),
    (["rise", "win", "top", "king", "queen", "champion", "power"], "triumph"),
    (["money", "hustle", "grind", "work", "paper", "cash", "rich"], "hustle"),
    (["god", "grace", "pray", "bless", "faith", "holy", "spirit"], "spirituality"),
    (["summer", "memory", "back", "remember", "old", "young", "days"], "nostalgia"),
    (["rebel", "free", "wild", "break", "fight", "run", "escape"], "rebellion"),
    (["city", "street", "block", "hood", "world", "road"], "journey"),
    (["fire", "heat", "burn", "flame", "electric", "thunder", "spark"], "energy"),
]

# ─── Acoustic feature → theme mapping ────────────────────────────────────────


def _valence_energy_theme(valence: float, energy: float) -> Optional[str]:
    """Map acoustic vectors to primary emotional theme."""
    if valence >= 0.7 and energy >= 0.7:
        return "confidence"
    if valence >= 0.6 and energy >= 0.5:
        return "euphoria"
    if valence <= 0.35 and energy <= 0.45:
        return "heartbreak"
    if valence <= 0.4 and energy >= 0.65:
        return "tension"
    if valence >= 0.5 and energy <= 0.4:
        return "romance"
    return None


# ─── Genre → theme modifiers ──────────────────────────────────────────────────

_GENRE_THEMES: dict[str, list[str]] = {
    "country": ["nostalgia", "journey"],
    "hip_hop": ["hustle", "triumph"],
    "rnb": ["romance", "nightlife"],
    "gospel": ["spirituality", "triumph"],
    "electronic": ["nightlife", "energy"],
    "metal": ["rebellion", "energy"],
    "alternative": ["rebellion", "journey"],
    "folk": ["nostalgia", "journey"],
    "latin": ["romance", "nightlife"],
    "afrobeats": ["nightlife", "euphoria"],
}


# ─── Main Inference Function ──────────────────────────────────────────────────


def infer_themes(
    title: str,
    genres: List[str],
    valence: Optional[float] = None,
    energy: Optional[float] = None,
    max_themes: int = 3,
) -> List[str]:
    """
    Infer lyric themes from title keywords, genres, and acoustic features.
    Safe: never reads or uses actual lyrics.
    Returns up to max_themes canonical theme labels.
    """
    title_lower = title.lower()
    themes: list[str] = []

    # 1. Title keyword inference
    for keywords, theme in _TITLE_RULES:
        if any(kw in title_lower for kw in keywords):
            if theme not in themes:
                themes.append(theme)

    # 2. Acoustic feature inference
    if valence is not None and energy is not None:
        acoustic_theme = _valence_energy_theme(valence, energy)
        if acoustic_theme and acoustic_theme not in themes:
            themes.insert(0, acoustic_theme)  # Acoustic inference gets priority

    # 3. Genre modifier
    for genre in genres:
        for genre_theme in _GENRE_THEMES.get(genre, []):
            if genre_theme not in themes:
                themes.append(genre_theme)

    # Deduplicate and cap
    seen: set[str] = set()
    result: list[str] = []
    for t in themes:
        if t not in seen:
            seen.add(t)
            result.append(t)
        if len(result) >= max_themes:
            break

    return result or ["emotion", "storytelling"]

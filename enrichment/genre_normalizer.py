"""
enrichment/genre_normalizer.py

Normalizes raw genre strings from MusicBrainz / Spotify into canonical genre keys.
Maps messy free-text genre strings like "hip hop/rap" → "hip_hop".
"""

from typing import List

# Ordered by priority (more specific first)
_GENRE_RULES: list[tuple[list[str], str]] = [
    (["k-pop", "kpop", "korean pop"], "kpop"),
    (["afrobeats", "afropop", "amapiano"], "afrobeats"),
    (["latin", "reggaeton", "salsa", "cumbia", "bachata"], "latin"),
    (["gospel", "christian", "praise"], "gospel"),
    (["reggae", "dancehall", "ska"], "reggae"),
    (["metal", "thrash", "death metal", "heavy metal", "metalcore"], "metal"),
    (["punk", "post-punk", "emo"], "rock"),
    (["alternative", "indie rock", "grunge", "shoegaze"], "alternative"),
    (["rock", "classic rock", "arena rock", "soft rock"], "rock"),
    (["folk", "americana", "bluegrass", "singer-songwriter"], "folk"),
    (["jazz", "jazz fusion", "smooth jazz", "bebop"], "jazz"),
    (["electronic", "edm", "house", "techno", "trance", "drum and bass"], "electronic"),
    (["dance", "disco", "dance pop", "club"], "electronic"),
    (["hip hop", "hip-hop", "rap", "trap", "drill", "boom bap"], "hip_hop"),
    (["r&b", "rnb", "soul", "neo-soul", "funk"], "rnb"),
    (["country", "country pop", "bluegrass", "honky tonk"], "country"),
    (["pop"], "pop"),
]


def normalize_genre(raw: str) -> str:
    """Map a raw genre string to a canonical genre key."""
    cleaned = raw.lower().strip()
    for keywords, canonical in _GENRE_RULES:
        if any(kw in cleaned for kw in keywords):
            return canonical
    return "pop"  # Default fallback


def normalize_genres(raw_list: List[str]) -> List[str]:
    """Deduplicate and normalize a list of raw genre strings."""
    seen = set()
    result = []
    for raw in raw_list:
        canonical = normalize_genre(raw)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result or ["pop"]

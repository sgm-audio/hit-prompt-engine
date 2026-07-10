"""
ingestion/genre_chart_mapper.py

Maps Billboard genre chart names to canonical genre labels.
Used when populating genre metadata from chart source data.
"""

import yaml
from pathlib import Path
from typing import Optional

_taxonomy: dict = {}


def _load_taxonomy() -> dict:
    global _taxonomy
    if not _taxonomy:
        taxonomy_path = Path(__file__).parent.parent / "config" / "genre_taxonomy.yaml"
        with open(taxonomy_path) as f:
            raw = yaml.safe_load(f)
        _taxonomy = raw.get("genres", {})
    return _taxonomy


CHART_TO_GENRE: dict[str, str] = {
    "hot-100": "pop",
    "r-b-hip-hop-songs": "rnb",
    "country-songs": "country",
    "pop-songs": "pop",
    "rock-songs": "rock",
    "latin-songs": "latin",
    "dance-electronic-songs": "electronic",
    "rap-songs": "hip_hop",
    "alternative-songs": "alternative",
    "adult-contemporary": "pop",
    "gospel-songs": "gospel",
    "reggae-songs": "reggae",
    "k-pop": "kpop",
    "afrobeats": "afrobeats",
}


def chart_to_canonical_genre(chart_name: str) -> Optional[str]:
    """Map a chart name to a canonical genre key."""
    return CHART_TO_GENRE.get(chart_name)


def canonical_genre_to_suno_tags(genre_key: str) -> list[str]:
    """Get Suno style tags for a canonical genre key."""
    taxonomy = _load_taxonomy()
    genre_data = taxonomy.get(genre_key, {})
    return genre_data.get("suno_tags", [genre_key])


def chart_to_suno_tags(chart_name: str) -> list[str]:
    """End-to-end: chart name → Suno-ready style tags."""
    genre_key = chart_to_canonical_genre(chart_name)
    if not genre_key:
        return []
    return canonical_genre_to_suno_tags(genre_key)

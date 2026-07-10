"""
tests/conftest.py — Shared pytest fixtures for hit-prompt-engine.
"""

import pytest
import sqlite3
import tempfile
import os

from dna.dna_schema import TrackDNA


# ─── TrackDNA fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def minimal_dna() -> TrackDNA:
    """Bare-minimum valid TrackDNA — only required fields."""
    return TrackDNA(
        track_id="trk_test001",
        title="Test Track",
        artist="Test Artist",
        release_year=2020,
        genres=["pop"],
    )


@pytest.fixture
def full_dna() -> TrackDNA:
    """Fully populated TrackDNA simulating Phase 1 + Phase 2 complete."""
    return TrackDNA(
        track_id="trk_billie001",
        title="Midnight Drive",
        artist="Test Artist",
        release_year=2019,
        genres=["pop", "electronic"],
        mbid="abc123-mb",
        isrc="USUM71900001",
        spotify_id="4iV5W9uYEdYUVa79Axb7Rh",
        bpm=135.2,
        key="A minor",
        mode="minor",
        energy=0.82,
        valence=0.61,
        danceability=0.88,
        acousticness=0.03,
        instrumentalness=0.0,
        structure=[
            "intro",
            "verse",
            "chorus",
            "verse",
            "chorus",
            "bridge",
            "chorus",
            "outro",
        ],
        energy_curve={"intro": 0.4, "verse": 0.6, "chorus": 0.9, "bridge": 0.7},
        instrumentation=["synthesizer", "drum_machine", "bass"],
        production_tags=["sidechain_pump", "reverb_wash"],
        vocal_profile="female_pop",
        lyric_themes=["nightlife", "euphoria"],
        uniqueness_hooks=["driving_synth_arp", "anthemic_chorus"],
        analysis_version="2.0",
        preview_analyzed=True,
    )


@pytest.fixture
def hip_hop_dna() -> TrackDNA:
    return TrackDNA(
        track_id="trk_hiphop001",
        title="Paper Chase",
        artist="Test Rapper",
        release_year=2018,
        genres=["hip_hop"],
        bpm=88.0,
        key="C minor",
        mode="minor",
        energy=0.74,
        valence=0.42,
        danceability=0.78,
        vocal_profile="rap_male",
        lyric_themes=["hustle", "triumph"],
    )


@pytest.fixture
def acoustic_dna() -> TrackDNA:
    return TrackDNA(
        track_id="trk_acoustic001",
        title="Sunday Morning",
        artist="Test Singer",
        release_year=2005,
        genres=["folk", "country"],
        bpm=72.0,
        key="G major",
        mode="major",
        energy=0.28,
        valence=0.68,
        acousticness=0.91,
        vocal_profile="male_pop",
        lyric_themes=["nostalgia", "romance"],
    )


@pytest.fixture
def eighties_dna() -> TrackDNA:
    return TrackDNA(
        track_id="trk_80s001",
        title="Neon Streets",
        artist="Test Band",
        release_year=1985,
        genres=["rock", "pop"],
        bpm=118.0,
        key="E major",
        mode="major",
        energy=0.79,
        valence=0.71,
        instrumentation=["electric_guitar", "synth", "drum_machine"],
        production_tags=["gated_reverb", "DX7_keys"],
        vocal_profile="male_rock",
        lyric_themes=["rebellion", "energy"],
    )


# ─── DB fixtures ──────────────────────────────────────────────────────────────


def _unlink_sqlite(path: str) -> None:
    """Delete SQLite DB + WAL/SHM journal files (Windows-safe)."""
    for suffix in ("", "-wal", "-shm"):
        p = path + suffix
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass


@pytest.fixture
def temp_db():
    """Temporary SQLite database for deduper tests."""
    from ingestion.deduper import init_db

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    # init_db returns an open connection — close it before opening our own
    init_conn = init_db(db_path)
    init_conn.execute("PRAGMA journal_mode=DELETE")  # Flush WAL before close
    init_conn.close()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn

    conn.execute("PRAGMA journal_mode=DELETE")
    conn.close()
    _unlink_sqlite(db_path)

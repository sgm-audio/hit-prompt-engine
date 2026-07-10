"""
ingestion/deduper.py

Builds a deduplicated canonical track catalog from raw chart JSONs.
Deduplication strategy:
  1. ISRC (exact) — best
  2. MusicBrainz ID (from enrichment)
  3. Fuzzy artist+title match (rapidfuzz, 90% threshold)
"""

import json
import sqlite3
import hashlib
import re
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

DB_PATH = "data/canonical_tracks.db"


# ─── Schema ───────────────────────────────────────────────────────────────────


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            track_id        TEXT PRIMARY KEY,
            isrc            TEXT,
            title           TEXT NOT NULL,
            artist          TEXT NOT NULL,
            release_year    INTEGER,
            dedupe_key      TEXT,
            chart_count     INTEGER DEFAULT 1,
            peak_hot100     INTEGER,
            peak_genre      INTEGER,
            genre_charts    TEXT,       -- JSON array of charts this track appeared on
            weeks_on_chart  INTEGER,
            enriched        INTEGER DEFAULT 0,
            spotify_features_enriched INTEGER DEFAULT 0,
            deep_analyzed   INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tracks_dedupe ON tracks (dedupe_key);
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chart_entries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id        TEXT,
            chart           TEXT,
            chart_date      TEXT,
            rank            INTEGER,
            peak_position   INTEGER,
            weeks_on_chart  INTEGER,
            FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entries_track ON chart_entries (track_id);
    """)
    conn.commit()
    return conn


# ─── Dedup Logic ──────────────────────────────────────────────────────────────


def make_dedupe_key(title: str, artist: str) -> str:
    """Normalized fuzzy key: lowercase, stripped, no punctuation, no feat. etc."""

    def clean(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"\(.*?\)", "", s)  # Remove (feat. X), (remix), etc.
        s = re.sub(r"\[.*?\]", "", s)  # Remove [Explicit], etc.
        s = re.sub(r"[^a-z0-9\s]", "", s)
        return " ".join(s.split())

    return f"{clean(artist)}||{clean(title)}"


def fuzzy_find_existing(
    conn: sqlite3.Connection,
    title: str,
    artist: str,
    threshold: int = 90,
) -> Optional[str]:
    """Return track_id if a fuzzy match exists above threshold."""
    key = make_dedupe_key(title, artist)
    cursor = conn.execute("SELECT track_id, dedupe_key FROM tracks")
    for row in cursor:
        score = fuzz.ratio(key, row[1])
        if score >= threshold:
            return row[0]
    return None


def upsert_track(
    conn: sqlite3.Connection,
    title: str,
    artist: str,
    chart: str,
    chart_date: str,
    rank: int,
    peak_position: int,
    weeks_on_chart: int,
    isrc: Optional[str] = None,
    release_year: Optional[int] = None,
) -> str:
    """Insert or update a track; return track_id."""
    # Check for fuzzy duplicate
    existing_id = fuzzy_find_existing(conn, title, artist)

    if existing_id:
        # Update chart stats
        conn.execute(
            """
            UPDATE tracks SET
                chart_count = chart_count + 1,
                peak_hot100 = CASE
                    WHEN ? < peak_hot100 OR peak_hot100 IS NULL
                    THEN ? ELSE peak_hot100 END,
                weeks_on_chart = MAX(COALESCE(weeks_on_chart, 0), ?)
            WHERE track_id = ?
            """,
            (peak_position, peak_position, weeks_on_chart, existing_id),
        )
        track_id = existing_id
    else:
        # New track
        raw = f"{artist.lower()}|{title.lower()}"
        track_id = (
            "trk_" + hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO tracks
            (track_id, isrc, title, artist, release_year,
             dedupe_key, peak_hot100, weeks_on_chart, genre_charts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                track_id,
                isrc,
                title,
                artist,
                release_year,
                make_dedupe_key(title, artist),
                peak_position,
                weeks_on_chart,
                json.dumps([chart]),
            ),
        )

    # Always log the chart entry
    conn.execute(
        """
        INSERT INTO chart_entries
        (track_id, chart, chart_date, rank, peak_position, weeks_on_chart)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (track_id, chart, chart_date, rank, peak_position, weeks_on_chart),
    )

    conn.commit()
    return track_id


# ─── Main ─────────────────────────────────────────────────────────────────────


def build_canonical_catalog(
    raw_charts_dir: str = "data/raw_charts",
    db_path: str = DB_PATH,
):
    """Walk all raw chart JSONs → build deduplicated canonical catalog."""
    conn = init_db(db_path)
    chart_files = sorted(Path(raw_charts_dir).glob("*.json"))

    total_entries = 0
    for f in chart_files:
        data = json.loads(f.read_text())
        for chart_name, entries in data.get("charts", {}).items():
            for entry in entries:
                if not entry.get("title") or not entry.get("artist"):
                    continue
                upsert_track(
                    conn=conn,
                    title=entry["title"],
                    artist=entry["artist"],
                    chart=chart_name,
                    chart_date=entry["chart_date"],
                    rank=entry.get("rank", 100),
                    peak_position=entry.get("peak_position", entry.get("rank", 100)),
                    weeks_on_chart=entry.get("weeks_on_chart", 1),
                )
                total_entries += 1
        print(f"[OK] Processed {f.name} ({total_entries} total entries so far)")

    count = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    print(
        f"\n✅ Canonical catalog built: {count:,} unique tracks from {total_entries:,} entries"
    )
    conn.close()


if __name__ == "__main__":
    build_canonical_catalog()

"""
enrichment/musicbrainz_enricher.py

Enriches the canonical track catalog with MusicBrainz metadata:
  - MBID
  - ISRC
  - Duration
  - Genre tags
  - Release year (earliest known)

HARD RULES (enforced by MB Terms of Service):
  - Max 1 request/second — enforced with time.sleep()
  - Must set a valid User-Agent string (your@email.com)
  - Exceeding rate limit risks IP block
"""

import time
import sqlite3
import httpx
from typing import Optional

MB_BASE = "https://musicbrainz.org/ws/2"
USER_AGENT = "HitPromptEngine/1.0 (contact@sgm-studios.com)"  # ← Update this


# ─── MB API Helpers ───────────────────────────────────────────────────────────


def mb_search_recording(
    client: httpx.Client,
    title: str,
    artist: str,
) -> Optional[dict]:
    """
    Search MusicBrainz for a recording by title + artist.
    Returns normalized metadata or None.
    Throttle: 1 req/sec enforced externally.
    """
    query = f'recording:"{title}" AND artist:"{artist}"'
    r = client.get(
        f"{MB_BASE}/recording",
        params={"query": query, "limit": 3, "fmt": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    if r.status_code != 200:
        return None

    results = r.json().get("recordings", [])
    if not results:
        return None

    # Take highest-score result
    best = results[0]
    return {
        "mbid": best.get("id"),
        "isrc": (best.get("isrcs") or [None])[0],
        "duration_ms": best.get("length"),
        "genres": [t["name"] for t in best.get("tags", [])[:5]],
        "release_year": _extract_year(best),
        "mb_score": best.get("score", 0),
    }


def _extract_year(recording: dict) -> Optional[int]:
    """Pull earliest release year from recording releases."""
    releases = recording.get("releases", [])
    years = []
    for r in releases:
        date_str = r.get("date", "")
        if date_str and len(date_str) >= 4:
            try:
                years.append(int(date_str[:4]))
            except ValueError:
                pass
    return min(years) if years else None


# ─── Enrichment Runner ────────────────────────────────────────────────────────


def enrich_catalog(
    db_path: str = "data/canonical_tracks.db",
    limit: Optional[int] = None,
):
    """
    Enrich all unenriched tracks in the catalog with MusicBrainz data.
    Respects 1 req/sec rate limit strictly.
    """
    conn = sqlite3.connect(db_path)

    # Add enrichment columns if not present
    for col_def in [
        "mbid TEXT",
        "duration_ms INTEGER",
        "mb_genres TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE tracks ADD COLUMN {col_def}")
            conn.commit()
        except Exception:  # nosec B110
            pass  # Column already exists

    query = "SELECT track_id, title, artist FROM tracks WHERE enriched = 0 OR enriched IS NULL"
    if limit:
        query += f" LIMIT {limit}"

    tracks = conn.execute(query).fetchall()
    print(f"🔍 Enriching {len(tracks):,} tracks via MusicBrainz...")

    with httpx.Client() as client:
        for i, (track_id, title, artist) in enumerate(tracks):
            t_start = time.monotonic()

            result = mb_search_recording(client, title, artist)

            if result:
                conn.execute(
                    """
                    UPDATE tracks SET
                        mbid = ?,
                        isrc = COALESCE(isrc, ?),
                        duration_ms = ?,
                        release_year = COALESCE(release_year, ?),
                        mb_genres = ?,
                        enriched = 1
                    WHERE track_id = ?
                    """,
                    (
                        result["mbid"],
                        result["isrc"],
                        result["duration_ms"],
                        result["release_year"],
                        str(result["genres"]),
                        track_id,
                    ),
                )
                conn.commit()
            else:
                # Mark as enrichment-attempted so we don't retry constantly
                conn.execute(
                    "UPDATE tracks SET enriched = -1 WHERE track_id = ?",
                    (track_id,),
                )
                conn.commit()

            if i % 100 == 0:
                print(f"  [{i}/{len(tracks)}] Enriched: {artist} — {title}")

            # ✅ Enforce 1 req/sec hard limit
            elapsed = time.monotonic() - t_start
            sleep_time = max(0, 1.0 - elapsed)
            time.sleep(sleep_time)

    enriched_count = conn.execute(
        "SELECT COUNT(*) FROM tracks WHERE enriched = 1"
    ).fetchone()[0]
    print(f"\n✅ Enrichment complete: {enriched_count:,} tracks enriched")
    conn.close()
    return enriched_count


if __name__ == "__main__":
    enrich_catalog(limit=500)  # Start with 500 to test

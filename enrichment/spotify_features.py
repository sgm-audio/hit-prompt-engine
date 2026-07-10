"""
enrichment/spotify_features.py

Enriches tracks with audio features (BPM, key, energy, valence, etc.)
via the Spotify Extended Audio Features endpoint on RapidAPI.

This approach avoids the Spotify SDK and works with the public RapidAPI
mirror that provides audio features data reliably in 2026.
"""

import asyncio
import sqlite3
from typing import Optional

import httpx

RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY"  # ← Set via env var in production
HOST = "spotify23.p.rapidapi.com"  # Current reliable Spotify proxy on RapidAPI

HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# ─── Key conversion ────────────────────────────────────────────────────────────

_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _key_to_string(key_num: int, mode: int) -> str:
    note = _NOTES[key_num % 12] if 0 <= key_num < 12 else "C"
    quality = "major" if mode == 1 else "minor"
    return f"{note} {quality}"


# ─── Spotify Search ────────────────────────────────────────────────────────────


async def get_spotify_track_id(
    client: httpx.AsyncClient,
    title: str,
    artist: str,
) -> Optional[str]:
    """Search for Spotify track ID via title + artist."""
    url = f"https://{HOST}/search/"
    params = {"q": f"{title} {artist}", "type": "tracks", "offset": "0", "limit": "1"}
    try:
        r = await client.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        items = r.json().get("tracks", {}).get("items", [])
        if items:
            return items[0].get("id")
    except Exception as e:
        print(f"[WARN] Spotify search failed for '{title}' by '{artist}': {e}")
    return None


async def fetch_audio_features(
    client: httpx.AsyncClient,
    spotify_id: str,
) -> Optional[dict]:
    """Fetch audio features for a Spotify track ID."""
    url = f"https://{HOST}/audio-features/"
    params = {"ids": spotify_id}
    try:
        r = await client.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        features_list = r.json().get("audio_features", [])
        if not features_list or not features_list[0]:
            return None
        data = features_list[0]
        return {
            "bpm": data.get("tempo"),
            "key": _key_to_string(data.get("key", 0), data.get("mode", 1)),
            "mode": "major" if data.get("mode", 1) == 1 else "minor",
            "energy": data.get("energy"),
            "valence": data.get("valence"),
            "danceability": data.get("danceability"),
            "acousticness": data.get("acousticness"),
            "instrumentalness": data.get("instrumentalness"),
            "duration_ms": data.get("duration_ms"),
        }
    except Exception as e:
        print(f"[WARN] Audio features failed for id={spotify_id}: {e}")
    return None


# ─── Batch Enrichment ─────────────────────────────────────────────────────────


def enrich_with_features(
    db_path: str = "data/canonical_tracks.db",
    batch_size: int = 200,
):
    """Batch enrich tracks with Spotify audio features."""
    conn = sqlite3.connect(db_path)

    # Add columns
    for col_def in [
        "bpm REAL",
        "key TEXT",
        "mode TEXT",
        "energy REAL",
        "valence REAL",
        "danceability REAL",
        "acousticness REAL",
        "instrumentalness REAL",
        "spotify_id TEXT",
        "spotify_features_enriched INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(f"ALTER TABLE tracks ADD COLUMN {col_def}")
            conn.commit()
        except Exception:  # nosec B110
            pass

    tracks = conn.execute(
        """
        SELECT track_id, title, artist FROM tracks
        WHERE spotify_features_enriched = 0 OR spotify_features_enriched IS NULL
        LIMIT ?
        """,
        (batch_size,),
    ).fetchall()

    print(f"🎵 Fetching Spotify features for {len(tracks):,} tracks...")

    async def _run():
        async with httpx.AsyncClient() as client:
            for i, (track_id, title, artist) in enumerate(tracks):
                spotify_id = await get_spotify_track_id(client, title, artist)
                if not spotify_id:
                    conn.execute(
                        "UPDATE tracks SET spotify_features_enriched = -1 WHERE track_id = ?",
                        (track_id,),
                    )
                    conn.commit()
                    continue

                features = await fetch_audio_features(client, spotify_id)
                if features:
                    conn.execute(
                        """
                        UPDATE tracks SET
                            spotify_id = ?,
                            bpm = ?,
                            key = ?,
                            mode = ?,
                            energy = ?,
                            valence = ?,
                            danceability = ?,
                            acousticness = ?,
                            instrumentalness = ?,
                            spotify_features_enriched = 1
                        WHERE track_id = ?
                        """,
                        (
                            spotify_id,
                            features["bpm"],
                            features["key"],
                            features["mode"],
                            features["energy"],
                            features["valence"],
                            features["danceability"],
                            features["acousticness"],
                            features["instrumentalness"],
                            track_id,
                        ),
                    )
                    conn.commit()

                if i % 50 == 0:
                    print(f"  [{i}/{len(tracks)}] {artist} — {title}")

                await asyncio.sleep(0.3)  # Polite rate limit

    asyncio.run(_run())

    enriched = conn.execute(
        "SELECT COUNT(*) FROM tracks WHERE spotify_features_enriched = 1"
    ).fetchone()[0]
    print(f"\n✅ Spotify features done: {enriched:,} tracks enriched")
    conn.close()


if __name__ == "__main__":
    enrich_with_features(batch_size=100)

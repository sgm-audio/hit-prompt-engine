"""
run_pipeline.py

Master runner for the Hit Prompt Engine.
Executes Phase 1 (ingestion + enrichment) and Phase 2 (audio DNA) in sequence.

Usage:
    python run_pipeline.py --help
    python run_pipeline.py phase1 --start 2020-01-01 --end 2024-12-31
    python run_pipeline.py phase2 --limit 500
    python run_pipeline.py all --start 1976-01-01 --end 2026-01-01
    python run_pipeline.py serve
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")

DB_PATH = os.environ.get("HIT_ENGINE_DB", "hit_engine.db")


# ─── Phase 1 ──────────────────────────────────────────────────────────────────


async def run_phase1(start: str, end: str, charts: list[str] | None = None) -> None:
    from ingestion.billboard_puller import ingest_date_range
    from ingestion.deduper import init_db
    from enrichment.musicbrainz_enricher import enrich_catalog
    from enrichment.spotify_features import enrich_with_features

    log.info("=== PHASE 1: INGESTION + ENRICHMENT ===")
    log.info(f"Date range: {start} → {end}")

    # 1. Init DB
    init_db(DB_PATH)
    log.info(f"DB initialized: {DB_PATH}")

    # 2. Ingest Billboard
    chart_list = charts or ["hot-100"]
    log.info(f"Ingesting charts: {chart_list}")
    await ingest_date_range(
        db_path=DB_PATH,
        start_date=start,
        end_date=end,
        charts=chart_list,
    )

    # 3. MusicBrainz enrichment
    log.info("Enriching with MusicBrainz metadata (1 req/sec — be patient)...")
    enrich_catalog(db_path=DB_PATH)

    # 4. Spotify audio features
    log.info("Enriching with Spotify audio features...")
    enrich_with_features(db_path=DB_PATH)

    log.info("Phase 1 complete.")


# ─── Phase 2 ──────────────────────────────────────────────────────────────────


def run_phase2(
    limit: int | None = None,
    audio_dir: str = "audio_cache",
    skip_download: bool = False,
) -> None:
    from dna.audio_analyzer import analyze_audio
    from dna.feature_extractor import extract_features
    from dna.theme_extractor import infer_themes
    import json

    log.info("=== PHASE 2: AUDIO DNA EXTRACTION ===")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Fetch tracks that need DNA
    query = """
        SELECT track_id, title, artist, genres, bpm, energy, valence,
               release_year
        FROM tracks
        WHERE instrumentation IS NULL
        ORDER BY peak_position ASC
    """
    if limit:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    log.info(f"Tracks to process: {len(rows)}")

    audio_path_root = Path(audio_dir)
    audio_path_root.mkdir(exist_ok=True)

    updated = 0
    skipped = 0

    for row in rows:
        track_id = row["track_id"]
        title = row["title"]
        artist = row["artist"]

        # Look for cached audio file
        audio_file: Path | None = None
        for ext in (".mp3", ".wav", ".flac", ".m4a"):
            candidate = audio_path_root / f"{track_id}{ext}"
            if candidate.exists():
                audio_file = candidate
                break

        genres_raw = row["genres"] or "[]"
        try:
            genres = json.loads(genres_raw)
        except (json.JSONDecodeError, TypeError):
            genres = []

        # Theme inference (no audio needed)
        themes = infer_themes(
            title=title,
            genres=genres,
            valence=row["valence"],
            energy=row["energy"],
        )

        instrumentation = None
        production_tags = None
        structure = None
        energy_curve = None

        if audio_file:
            log.info(f"  Analyzing: {title} — {artist}")
            try:
                analysis = analyze_audio(str(audio_file))
                features = extract_features(str(audio_file))

                if analysis is None:
                    log.warning(f"  Audio analysis returned None for {track_id}")
                    skipped += 1
                else:
                    structure = json.dumps(analysis.structure)
                    energy_curve = json.dumps(analysis.energy_curve)
                    instrumentation = json.dumps(features.instrumentation[:5])
                    production_tags = json.dumps(features.production_tags[:4])
                    updated += 1
            except Exception as exc:
                log.warning(f"  Audio analysis failed for {track_id}: {exc}")
                skipped += 1
        else:
            log.debug(f"  No audio file for {track_id} — themes only")
            skipped += 1

        conn.execute(
            """
            UPDATE tracks
            SET lyric_themes = ?,
                instrumentation = ?,
                production_tags = ?,
                structure = ?,
                energy_curve = ?
            WHERE track_id = ?
            """,
            (
                json.dumps(themes),
                instrumentation,
                production_tags,
                structure,
                energy_curve,
                track_id,
            ),
        )

    conn.commit()
    conn.close()
    log.info(f"Phase 2 complete. Audio DNA: {updated} tracks. Themes only: {skipped}.")


# ─── Serve ────────────────────────────────────────────────────────────────────


def run_serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    try:
        import uvicorn
    except ImportError:
        log.error("uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    log.info(f"Starting API server on http://{host}:{port}")
    uvicorn.run("api.prompt_library:app", host=host, port=port, reload=False)


# ─── CLI ──────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_pipeline",
        description="Hit Prompt Engine — master runner",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # phase1
    p1 = sub.add_parser("phase1", help="Ingest Billboard + enrich metadata")
    p1.add_argument("--start", default="2020-01-01", help="Start date YYYY-MM-DD")
    p1.add_argument("--end", default="2024-12-31", help="End date YYYY-MM-DD")
    p1.add_argument("--charts", nargs="+", default=["hot-100"])

    # phase2
    p2 = sub.add_parser("phase2", help="Audio DNA extraction")
    p2.add_argument("--limit", type=int, default=None, help="Max tracks to process")
    p2.add_argument(
        "--audio-dir", default="audio_cache", help="Directory with audio files"
    )
    p2.add_argument("--skip-download", action="store_true")

    # all
    pa = sub.add_parser("all", help="Run Phase 1 then Phase 2")
    pa.add_argument("--start", default="1976-01-01")
    pa.add_argument("--end", default="2026-01-01")
    pa.add_argument("--charts", nargs="+", default=["hot-100"])
    pa.add_argument("--phase2-limit", type=int, default=None)
    pa.add_argument("--audio-dir", default="audio_cache")

    # serve
    ps = sub.add_parser("serve", help="Start FastAPI server")
    ps.add_argument("--host", default="0.0.0.0")
    ps.add_argument("--port", type=int, default=8000)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    t0 = time.time()

    if args.command == "phase1":
        asyncio.run(run_phase1(args.start, args.end, args.charts))

    elif args.command == "phase2":
        run_phase2(
            limit=args.limit,
            audio_dir=args.audio_dir,
            skip_download=args.skip_download,
        )

    elif args.command == "all":
        asyncio.run(run_phase1(args.start, args.end, args.charts))
        run_phase2(limit=args.phase2_limit, audio_dir=args.audio_dir)

    elif args.command == "serve":
        run_serve(args.host, args.port)

    elapsed = time.time() - t0
    if args.command != "serve":
        log.info(f"Done in {elapsed:.1f}s")


if __name__ == "__main__":
    main()

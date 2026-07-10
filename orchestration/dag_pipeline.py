"""
orchestration/dag_pipeline.py

Dagster pipeline for the Hit Prompt Engine.
Provides a visual DAG, retry logic, and incremental scheduling.

Run locally:
    dagster dev -f orchestration/dag_pipeline.py

Or via docker compose --profile orchestration up
"""

from __future__ import annotations

import os
import sqlite3
import asyncio
from datetime import datetime

from dagster import (
    AssetExecutionContext,
    Definitions,
    RunConfig,
    ScheduleDefinition,
    asset,
    define_asset_job,
    Config,
)

DB_PATH = os.environ.get("HIT_ENGINE_DB", "hit_engine.db")


# ─── Config ───────────────────────────────────────────────────────────────────


class Phase1Config(Config):
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    charts: str = "hot-100"  # comma-separated


class Phase2Config(Config):
    limit: int = 0  # 0 = no limit
    audio_dir: str = "audio_cache"


# ─── Assets ───────────────────────────────────────────────────────────────────


@asset(description="Initialize the SQLite database schema")
def db_initialized(context: AssetExecutionContext) -> None:
    from ingestion.deduper import init_db

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.close()
    context.log.info(f"DB ready: {DB_PATH}")


@asset(
    deps=[db_initialized],
    description="Ingest Billboard chart data for the configured date range",
)
def billboard_ingested(context: AssetExecutionContext, config: Phase1Config) -> int:
    from ingestion.billboard_puller import ingest_date_range

    charts = [c.strip() for c in config.charts.split(",")]
    context.log.info(
        f"Ingesting {charts} from {config.start_date} to {config.end_date}"
    )

    result = asyncio.run(
        ingest_date_range(
            db_path=DB_PATH,
            start_date=config.start_date,
            end_date=config.end_date,
            charts=charts,
        )
    )
    context.log.info(f"Ingested {result} chart entries")
    return result


@asset(
    deps=[billboard_ingested],
    description="Enrich tracks with MusicBrainz metadata (MBID, ISRC, duration)",
)
def musicbrainz_enriched(context: AssetExecutionContext) -> int:
    from enrichment.musicbrainz_enricher import enrich_catalog

    count = enrich_catalog(db_path=DB_PATH)
    context.log.info(f"MusicBrainz enriched: {count} tracks")
    return count


@asset(
    deps=[billboard_ingested],
    description="Enrich tracks with Spotify audio features (BPM, key, energy, valence)",
)
def spotify_enriched(context: AssetExecutionContext) -> int:
    from enrichment.spotify_features import enrich_with_features

    count = asyncio.run(enrich_with_features(db_path=DB_PATH))
    context.log.info(f"Spotify enriched: {count} tracks")
    return count


@asset(
    deps=[spotify_enriched, musicbrainz_enriched],
    description="Extract audio DNA: structure, energy curve, instrumentation (PANNs + librosa)",
)
def audio_dna_extracted(context: AssetExecutionContext, config: Phase2Config) -> int:
    import json
    from dna.audio_analyzer import analyze_audio
    from dna.feature_extractor import extract_features
    from dna.theme_extractor import infer_themes
    from pathlib import Path

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT track_id, title, artist, genres, valence, energy
        FROM tracks
        WHERE instrumentation IS NULL
        ORDER BY peak_position ASC
    """
    if config.limit:
        query += f" LIMIT {config.limit}"

    rows = conn.execute(query).fetchall()
    context.log.info(f"Tracks to process: {len(rows)}")

    audio_root = Path(config.audio_dir)
    updated = 0

    for row in rows:
        track_id = row["track_id"]
        genres = json.loads(row["genres"] or "[]")
        themes = infer_themes(
            title=row["title"],
            genres=genres,
            valence=row["valence"],
            energy=row["energy"],
        )

        instrumentation = production_tags = structure = energy_curve = None

        for ext in (".mp3", ".wav", ".flac", ".m4a"):
            audio_file = audio_root / f"{track_id}{ext}"
            if audio_file.exists():
                try:
                    analysis = analyze_audio(str(audio_file))
                    features = extract_features(str(audio_file))
                    structure = json.dumps(analysis.structure)
                    energy_curve = json.dumps(analysis.energy_curve)
                    instrumentation = json.dumps(features.instrumentation[:5])
                    production_tags = json.dumps(features.production_tags[:4])
                    updated += 1
                except Exception as exc:
                    context.log.warning(f"Audio analysis failed for {track_id}: {exc}")
                break

        conn.execute(
            """
            UPDATE tracks SET lyric_themes=?, instrumentation=?, production_tags=?,
                               structure=?, energy_curve=?
            WHERE track_id=?
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
    context.log.info(f"DNA complete — {updated} tracks with audio analysis")
    return updated


@asset(
    deps=[audio_dna_extracted],
    description="Pre-compile and lint all 6-variation prompt packs, store results",
)
def prompts_compiled(context: AssetExecutionContext) -> int:
    import json
    from dna.dna_schema import TrackDNA
    from prompt_compiler.variation_engine import export_prompt_pack_json
    from prompt_compiler.prompt_linter import lint_prompt

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT * FROM tracks").fetchall()
    context.log.info(f"Compiling prompts for {len(rows)} tracks")

    compiled = 0
    lint_failures = 0

    for row in rows:
        d = dict(row)
        for col in (
            "genres",
            "structure",
            "energy_curve",
            "instrumentation",
            "production_tags",
            "lyric_themes",
            "uniqueness_hooks",
        ):
            if d.get(col):
                try:
                    d[col] = json.loads(d[col])
                except (json.JSONDecodeError, TypeError):
                    pass

        try:
            dna = TrackDNA(**d)
            pack = export_prompt_pack_json(dna)
            passing = sum(
                1
                for v in pack["variations"]
                if lint_prompt(
                    v["suno_style"], v["suno_lyrics"], v["instrumental"]
                ).passed
            )
            if passing < 4:
                lint_failures += 1
            compiled += 1
        except Exception as exc:
            context.log.warning(f"Compile failed for {d.get('track_id')}: {exc}")

    conn.close()
    context.log.info(f"Compiled: {compiled}, lint <4/6 passing: {lint_failures}")
    return compiled


# ─── Jobs ─────────────────────────────────────────────────────────────────────

full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=[
        db_initialized,
        billboard_ingested,
        musicbrainz_enriched,
        spotify_enriched,
        audio_dna_extracted,
        prompts_compiled,
    ],
    description="Full Phase 1 + Phase 2 + compilation",
)

ingestion_only_job = define_asset_job(
    name="ingestion_only",
    selection=[
        db_initialized,
        billboard_ingested,
        musicbrainz_enriched,
        spotify_enriched,
    ],
)

# ─── Schedules ────────────────────────────────────────────────────────────────

weekly_ingestion = ScheduleDefinition(
    name="weekly_hot100_ingestion",
    job=ingestion_only_job,
    cron_schedule="0 9 * * 1",  # Monday 9am — Billboard updates weekly
    run_config=RunConfig(
        ops={
            "billboard_ingested": Phase1Config(
                start_date=datetime.utcnow().strftime("%Y-%m-%d"),
                end_date=datetime.utcnow().strftime("%Y-%m-%d"),
                charts="hot-100",
            )
        }
    ),
)

# ─── Definitions ──────────────────────────────────────────────────────────────

defs = Definitions(
    assets=[
        db_initialized,
        billboard_ingested,
        musicbrainz_enriched,
        spotify_enriched,
        audio_dna_extracted,
        prompts_compiled,
    ],
    jobs=[full_pipeline_job, ingestion_only_job],
    schedules=[weekly_ingestion],
)

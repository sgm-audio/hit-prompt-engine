# Changelog

All notable changes to Hit Prompt Engine are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.1.1] - 2026-07-10

### Fixed

- `billboard_puller.ingest_date_range` signature now matches callers (accepts `db_path`, `start_date`, `end_date`, `charts` and writes to DB directly)
- `dag_pipeline.db_initialized` passes path string to `init_db` instead of connection object
- `dag_pipeline.spotify_enriched` calls `enrich_with_features` synchronously (was wrapped in `asyncio.run`)
- `run_pipeline.run_phase1` calls `enrich_with_features` without `await` (sync function)
- `run_pipeline.run_phase2` guards against `None` return from `analyze_audio`
- `dag_pipeline.audio_dna_extracted` guards against `None` return from `analyze_audio`
- `enrich_catalog` and `enrich_with_features` now return `int` counts
- All ruff lint and format issues resolved
- All mypy type errors resolved in 26 source files

### Added

- Initial public release
- Phase 1: Billboard ingestion, MusicBrainz enrichment, Spotify audio features
- Phase 2: Audio DNA extraction (librosa + PANNs), theme inference
- Prompt compiler: 6-variation engine, style builder, lyrics builder, linter/scorer
- FastAPI REST API with catalog search and prompt pack generation
- Dagster orchestration pipeline with weekly scheduling
- Docker support (API + Redis + optional Dagster UI)
- GCP Cloud Run deployment (cloudbuild.yaml)

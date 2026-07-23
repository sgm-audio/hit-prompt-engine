# AGENTS.md — Hit Prompt Engine

> Compact operational facts an agent would miss without reading multiple files. README covers architecture, API, and quickstart — this covers the gotchas.

---

## Previously Broken Integration Points (fixed in v0.1.0)

All four signature mismatches between callers and callees have been fixed:

| File | Fix |
|------|-----|
| `ingestion/billboard_puller.py` | `ingest_date_range` now accepts `(db_path, start_date, end_date, charts)` and writes to DB |
| `orchestration/dag_pipeline.py` | `init_db(DB_PATH)` — passes string, not connection; `enrich_with_features` called directly (sync) |
| `enrichment/musicbrainz_enricher.py` | `enrich_catalog` now returns `int` count |
| `enrichment/spotify_features.py` | `enrich_with_features` now returns `int` count |

---

## Dead Code

- `db/models.py` — SQLAlchemy ORM (131 lines). **Imported by nothing.** All DB access is raw `sqlite3` in `deduper.py`. Exists as "upgrade path" per README but unused.

---

## Commands

```bash
# Phase 1 (metadata only, no audio needed)
python run_pipeline.py phase1 --start 2020-01-01 --end 2024-12-31

# Phase 2 (requires audio files in audio_cache/{track_id}.mp3|wav|flac|m4a)
python run_pipeline.py phase2 --limit 100 --audio-dir audio_cache

# Both phases
python run_pipeline.py all --start 1976-01-01 --end 2026-01-01

# API server
python run_pipeline.py serve --host 0.0.0.0 --port 8000

# Tests
pytest                          # all (no markers used despite pytest.ini defining them)
pytest tests/test_deduper.py    # single file
pytest -k "test_fuzzy"          # keyword filter

# Docker
docker compose up                       # API only (port 8000)
docker compose --profile orchestration up  # + Dagster UI (port 3000)

# GCP Cloud Run (via cloudbuild.yaml)
gcloud builds submit --config cloudbuild.yaml
```

---

## Test Gotchas

- `pytest.ini` defines markers `slow`, `integration`, `unit` — **no test file uses them**. `pytest -m slow` returns 0 tests.
- Fixtures in `tests/conftest.py`: `minimal_dna`, `full_dna`, `hip_hop_dna`, `acoustic_dna`, `eighties_dna`, `temp_db` (SQLite connection with schema).
- Untested modules: `audio_analyzer`, `feature_extractor`, `billboard_puller`, `musicbrainz_enricher`, `spotify_features`, `lyrics_builder`, `db/models`, `dag_pipeline`, `run_pipeline`, `genre_chart_mapper`, `api/prompt_library`.

---

## Audio Phase Prerequisites

- **No downloader exists.** You must provide audio files manually.
- Naming: `audio_cache/{track_id}.mp3` (or `.wav`, `.flac`, `.m4a`)
- `track_id` comes from `tracks` table (UUID-like string from deduper)
- Without audio: themes inferred from title/genre/valence/energy only; instrumentation/production/structure/energy_curve stay NULL

---

## Environment

```bash
cp .env.example .env
# Required: RAPIDAPI_KEY (Billboard genre charts + Spotify proxy)
# Optional: SPOTIFY_CLIENT_ID/SECRET (native API fallback)
# Optional: MUSICBRAINZ_CONTACT (User-Agent email)
# DB: HIT_ENGINE_DB=hit_engine.db (SQLite) or DATABASE_URL=postgresql://...
```

---

## No Lint/Format/Typecheck Tooling

- No `pyproject.toml`, `.flake8`, `mypy.ini`, `.pyright`, `.pre-commit-config.yaml`
- Do not attempt to run linters/formatters — they don't exist
- Code uses `from __future__ import annotations` + `TYPE_CHECKING` guards correctly

---

## Deployment (GCP)

`cloudbuild.yaml` does:
1. Build Docker image → Artifact Registry
2. Deploy API to Cloud Run (`hit-prompt-engine` service)
3. Update Cloud Run Job `hit-engine-weekly-ingest` with new image

Region: `us-central1` (substitution `_REGION`). Machine: `E2_HIGHCPU_8`.

---

## Key Module Coupling (what imports what)

```
run_pipeline.py, dag_pipeline.py  →  ALL modules (orchestration layer)
api/prompt_library.py             →  prompt_compiler.*, dna.dna_schema
prompt_compiler/variation_engine  →  prompt_compiler.style_builder, lyrics_builder
prompt_compiler/scorer            →  prompt_compiler.prompt_linter
prompt_compiler/style_builder     →  (TYPE_CHECKING) dna.dna_schema
prompt_compiler/lyrics_builder    →  (TYPE_CHECKING) dna.dna_schema
ingestion/*, enrichment/*, dna/*  →  stdlib only (self-contained islands)
db/models.py                      →  NOTHING (dead code)
```

---

## Config Files (all YAML, all complete)

- `config/hit_policy.yaml` — eligibility rules (peak position, weeks on chart, chart list)
- `config/genre_taxonomy.yaml` — 15 canonical genres → Suno tags
- `config/variation_recipes.yaml` — 6 variation blueprints (BPM deltas, style modifiers)

---

## Quick Verification Checklist

Before claiming a build works:
- [ ] `python run_pipeline.py phase1 --start 2024-01-01 --end 2024-01-07` completes without signature errors
- [ ] `pytest tests/test_deduper.py` passes
- [ ] `python run_pipeline.py serve` starts on port 8000, `curl localhost:8000/health` returns 200
- [ ] `docker compose up` brings up API + Redis
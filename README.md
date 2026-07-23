# Hit Prompt Engine

[![CI](https://github.com/sgm-audio/hit-prompt-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/sgm-audio/hit-prompt-engine/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Docs](https://img.shields.io/badge/docs-github--pages-blueviolet)](https://sgm-audio.github.io/hit-prompt-engine)

A data pipeline that turns 50 years of Billboard chart history into Suno-optimized prompt packs — copyright-safe, DNA-driven, six variations per track.

> **No Suno API calls.** This tool generates optimized prompts and manages track DNA. You paste the output into Suno Custom Mode.

---

## Architecture

```
Billboard Hot-100 (1976–2026)
         │
         ▼
  ┌─────────────────────┐
  │  Phase 1: Ingestion  │  billboard_puller → deduper → MusicBrainz → Spotify
  └─────────────────────┘
         │
         ▼
  ┌─────────────────────┐
  │  Phase 2: Audio DNA  │  librosa (BPM/key/structure) + PANNs (instruments/mood)
  └─────────────────────┘
         │
         ▼
  ┌─────────────────────┐
  │  Prompt Compiler     │  style_builder + lyrics_builder + 6-variation engine
  └─────────────────────┘
         │
         ▼
  ┌─────────────────────┐
  │  FastAPI / Dagster   │  REST API + visual DAG orchestration
  └─────────────────────┘
```

---

## Project Structure

```
hit-prompt-engine/
├── config/
│   ├── hit_policy.yaml          # Eligibility rules (peak, weeks, charts)
│   ├── genre_taxonomy.yaml      # 15 canonical genres → Suno tags
│   └── variation_recipes.yaml  # 6 variation blueprints
├── ingestion/
│   ├── billboard_puller.py      # Free Hot-100 JSON archive + RapidAPI genre charts
│   ├── deduper.py               # ISRC → MBID → fuzzy dedup (rapidfuzz 90%)
│   └── genre_chart_mapper.py   # Chart name → canonical genre key
├── enrichment/
│   ├── musicbrainz_enricher.py  # MBID, ISRC, duration (1 req/sec)
│   ├── spotify_features.py      # BPM, key, energy, valence, danceability
│   └── genre_normalizer.py     # Keyword normalization → canonical genre
├── dna/
│   ├── dna_schema.py            # Pydantic v2 TrackDNA model
│   ├── audio_analyzer.py        # librosa: BPM, key, structure segmentation
│   ├── feature_extractor.py     # PANNs AudioSet 527-label inference
│   └── theme_extractor.py       # Safe theme inference (title + acoustics, no lyrics)
├── prompt_compiler/
│   ├── style_builder.py         # 200-char Suno style field, 6 variation modes
│   ├── lyrics_builder.py        # Original lyric scaffolds, [Section] tags
│   ├── variation_engine.py      # 6-pack generator + JSON export
│   └── prompt_linter.py         # Quality gate: score 0–1, errors/warnings
├── api/
│   └── prompt_library.py        # FastAPI: /tracks, /prompts/{id}, /lint, /stats
├── db/
│   └── models.py                # SQLAlchemy ORM (SQLite dev / PostgreSQL prod)
├── orchestration/
│   └── dag_pipeline.py          # Dagster assets + weekly schedule
├── run_pipeline.py              # CLI master runner
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

For GPU-accelerated PANNs (optional, ~10× faster):
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run Phase 1 (no audio files needed)

```bash
# Last 5 years of Hot-100
python run_pipeline.py phase1 --start 2020-01-01 --end 2024-12-31

# Full 50-year catalog (takes hours — be patient with MusicBrainz 1 req/sec)
python run_pipeline.py phase1 --start 1976-01-01 --end 2026-01-01
```

### 4. Run Phase 2 (requires audio files)

Drop audio files (MP3/WAV/FLAC) named `{track_id}.mp3` into `audio_cache/`:

```bash
python run_pipeline.py phase2 --limit 100 --audio-dir audio_cache
```

### 5. Start the API

```bash
python run_pipeline.py serve
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### 6. Docker

```bash
docker compose up
# API: http://localhost:8000
# Dagster UI: docker compose --profile orchestration up → http://localhost:3000
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/tracks?q=&genre=&year_from=&year_to=` | Search catalog |
| GET | `/tracks/{track_id}` | Full TrackDNA |
| GET | `/prompts/{track_id}` | 6-variation prompt pack with lint scores |
| POST | `/lint` | Lint any style+lyrics pair on demand |
| GET | `/stats` | Catalog summary |

### Example: Get prompt pack

```bash
curl http://localhost:8000/prompts/abc123def456 | jq '.variations[0]'
```

```json
{
  "id": "V1_faithful",
  "name": "Faithful Essence",
  "suno_style": "pop, 118 BPM, high energy, driving rhythm, C major, ...",
  "suno_lyrics": "(Theme direction: gravity pulling us together)\n[Verse]\n...",
  "instrumental": false,
  "lint": { "passed": true, "score": 0.92, "warnings": [], "errors": [] }
}
```

---

## The 6 Variations

| ID | Name | Intent |
|----|------|--------|
| V1_faithful | Faithful Essence | Closest to original feel, fully original |
| V2_modern_2026 | Modern Radio 2026 | Updated mix, streaming-ready |
| V3_genre_bent | Genre-Bent | Cross-genre surprise, same emotional arc |
| V4_stripped | Stripped Acoustic | Minimal, intimate, acoustic-leaning |
| V5_instrumental | Instrumental Sync | Clean instrumental for sync licensing |
| V6_club_remix | Club Remix | Extended build/drop, DJ-friendly |

---

## Copyright Safety

This engine is designed from the ground up to be rights-safe:

- **No artist name injection** — style fields never contain artist names
- **No lyric copying** — `theme_extractor.py` infers from title keywords and acoustic features only; it never reads or references actual song lyrics
- **No song title injection** — style fields describe sonic DNA, not source material
- **Prompt linter** — automatically rejects prompts containing known artist names or iconic lyric fragments
- **Original scaffolds** — `lyrics_builder.py` generates structural direction blocks (`[Verse]`, producer cues) that guide Suno toward original compositions

---

## Legal

This tool processes publicly available chart metadata. Audio analysis (Phase 2) is performed on files you provide and own or have licensed. This project is not affiliated with Billboard, MusicBrainz, Spotify, or Suno AI.

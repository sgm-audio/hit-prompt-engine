# Architecture

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

## Module map

| Directory | Role |
|-----------|------|
| `ingestion/` | Billboard data pull, dedup (rapidfuzz), genre→chart mapping |
| `enrichment/` | MusicBrainz IDs, Spotify audio features, genre normalization |
| `dna/` | Audio analysis (librosa), PANNs inference, theme extraction |
| `prompt_compiler/` | Style field builder, lyrics scaffolds, 6 variations, linter+scorer |
| `api/` | FastAPI REST endpoints |
| `orchestration/` | Dagster asset pipeline + weekly schedule |
| `config/` | YAML: hit policy, genre taxonomy, variation recipes |

# Changelog

All notable changes to Hit Prompt Engine are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial public release
- Phase 1: Billboard ingestion, MusicBrainz enrichment, Spotify audio features
- Phase 2: Audio DNA extraction (librosa + PANNs), theme inference
- Prompt compiler: 6-variation engine, style builder, lyrics builder, linter/scorer
- FastAPI REST API with catalog search and prompt pack generation
- Dagster orchestration pipeline with weekly scheduling
- Docker support (API + Redis + optional Dagster UI)
- GCP Cloud Run deployment (cloudbuild.yaml)

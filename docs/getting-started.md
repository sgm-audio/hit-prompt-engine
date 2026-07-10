# Getting Started

## Prerequisites

- Python 3.11+
- API key for [RapidAPI](https://rapidapi.com/) (Billboard + Spotify proxy)
- Audio files (optional, for Phase 2)

## Install

```bash
pip install -r requirements.txt
```

For GPU-accelerated PANNs (~10× faster):

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Configure

```bash
cp .env.example .env
# Edit .env with your RapidAPI key
```

## Run Phase 1 (no audio files needed)

```bash
python run_pipeline.py phase1 --start 2024-01-01 --end 2024-12-31
```

This pulls Billboard chart data, deduplicates tracks, and enriches with
MusicBrainz and Spotify metadata.

## Run Phase 2 (requires audio files)

Drop `{track_id}.mp3` files into `audio_cache/`, then:

```bash
python run_pipeline.py phase2 --limit 100
```

## Start the API

```bash
python run_pipeline.py serve
# → http://localhost:8000/docs
```

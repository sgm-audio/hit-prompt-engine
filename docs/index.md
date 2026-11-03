# Hit Prompt Engine

A data pipeline that takes Billboard chart history (1976–2026) and turns it into Suno
prompt packs, with six variations per track. The prompt linter blocks artist names and
flags known lyric fragments. That's a check, not a copyright guarantee.

**No Suno API calls.** This tool generates optimized prompts and manages track DNA.
You paste the output into Suno Custom Mode.

---

## Why?

Suno Custom Mode requires two fields: a **style prompt** (200 chars) and **lyrics**.
Writing these by hand for bulk creation is tedious and inconsistent. This engine:

1. Ingests Billboard chart metadata (1976–present)
2. Enriches it with MusicBrainz IDs / Spotify audio features
3. Runs audio analysis via librosa + PANNs (BPM, key, structure, instrumentation)
4. Compiles 6 variations per track and lints them for artist names and lyric fragments
5. Scores each pack with a Pat Pattison–inspired linter

## Quick links

- [Getting Started](getting-started.md)
- [Architecture](architecture.md)
- [API Reference](api.md)
- [GitHub Repository](https://github.com/sgm-audio/hit-prompt-engine)

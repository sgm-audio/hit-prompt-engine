# Hit Prompt Engine

A data pipeline that turns 50 years of Billboard chart history into Suno-optimized
prompt packs — copyright-safe, DNA-driven, six variations per track.

**No Suno API calls.** This tool generates optimized prompts and manages track DNA.
You paste the output into Suno Custom Mode.

---

## Why?

Suno Custom Mode requires two fields: a **style prompt** (200 chars) and **lyrics**.
Writing these by hand for bulk creation is tedious and inconsistent. This engine:

1. Ingests Billboard chart metadata (1976–present)
2. Enriches it with MusicBrainz IDs / Spotify audio features
3. Runs audio analysis via librosa + PANNs (BPM, key, structure, instrumentation)
4. Compiles 6 copyright-safe variations per track
5. Scores each pack with a Pat Pattison–inspired linter

## Quick links

- [Getting Started](getting-started.md)
- [Architecture](architecture.md)
- [API Reference](api.md)
- [GitHub Repository](https://github.com/scottmills306/hit-prompt-engine)

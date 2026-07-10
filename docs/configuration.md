# Configuration

## Environment

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RAPIDAPI_KEY` | Yes | — | Billboard genre charts + Spotify proxy |
| `HIT_ENGINE_DB` | No | `hit_engine.db` | SQLite database path |
| `DATABASE_URL` | No | — | PostgreSQL connection string |
| `SPOTIFY_CLIENT_ID` | No | — | Native Spotify API fallback |
| `SPOTIFY_CLIENT_SECRET` | No | — | Native Spotify API fallback |
| `MUSICBRAINZ_CONTACT` | No | — | User-Agent email for MusicBrainz API |

## YAML configs

| File | Purpose |
|------|---------|
| `config/hit_policy.yaml` | Eligibility: peak position, weeks on chart, chart list |
| `config/genre_taxonomy.yaml` | 15 canonical genres mapped to Suno tags |
| `config/variation_recipes.yaml` | 6 variation blueprints with BPM deltas |

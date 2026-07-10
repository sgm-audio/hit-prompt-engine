# API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/tracks` | Search catalog (`?q=&genre=&year_from=&year_to=`) |
| GET | `/tracks/{track_id}` | Full TrackDNA |
| GET | `/prompts/{track_id}` | 6-variation prompt pack with lint scores |
| POST | `/lint` | Lint any style+lyrics pair |
| GET | `/stats` | Catalog summary |

## Example

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

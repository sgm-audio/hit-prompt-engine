"""
api/prompt_library.py

FastAPI serving layer for the Hit Prompt Engine.
Exposes compiled Suno prompt packs and track DNA over HTTP.

Endpoints:
  GET  /health
  GET  /tracks                  - Search/list tracks in catalog
  GET  /tracks/{track_id}       - Full TrackDNA for one track
  GET  /prompts/{track_id}      - 6-variation prompt pack for one track
  POST /lint                    - Lint a style+lyrics pair on demand
  GET  /stats                   - Catalog summary stats
"""

from __future__ import annotations

import sqlite3
import json
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from prompt_compiler.prompt_linter import lint_prompt
from prompt_compiler.variation_engine import export_prompt_pack_json
from dna.dna_schema import TrackDNA


# ─── Config ───────────────────────────────────────────────────────────────────

DB_PATH = os.environ.get("HIT_ENGINE_DB", "hit_engine.db")
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.environ.get("ENVIRONMENT", "development"),
    )


# ─── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Could warm caches / check DB here
    yield


app = FastAPI(
    title="Hit Prompt Engine API",
    version="0.1.1",
    description="Suno prompt packs generated from 50 years of chart DNA",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── DB Helpers ───────────────────────────────────────────────────────────────


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


# ─── Request / Response Models ────────────────────────────────────────────────


class LintRequest(BaseModel):
    style: str
    lyrics: str
    instrumental: bool = False


class LintResponse(BaseModel):
    passed: bool
    score: float
    warnings: List[str]
    errors: List[str]
    suggestions: List[str]


class TrackSummary(BaseModel):
    track_id: str
    title: str
    artist: str
    release_year: Optional[int]
    genres: List[str]
    bpm: Optional[float]
    peak_position: Optional[int]
    weeks_on_chart: Optional[int]


class CatalogPage(BaseModel):
    total: int
    page: int
    per_page: int
    results: List[TrackSummary]


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok", "db": DB_PATH}


@app.get("/tracks", response_model=CatalogPage)
def search_tracks(
    q: Optional[str] = Query(None, description="Search title or artist"),
    genre: Optional[str] = Query(None, description="Filter by canonical genre"),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    conn = get_db()
    try:
        where_clauses = []
        params: List[Any] = []

        if q:
            where_clauses.append("(LOWER(title) LIKE ? OR LOWER(artist) LIKE ?)")
            like = f"%{q.lower()}%"
            params.extend([like, like])
        if genre:
            where_clauses.append("LOWER(genres) LIKE ?")
            params.append(f"%{genre.lower()}%")
        if year_from:
            where_clauses.append("release_year >= ?")
            params.append(year_from)
        if year_to:
            where_clauses.append("release_year <= ?")
            params.append(year_to)

        count_sql = "SELECT COUNT(*) as cnt FROM tracks"
        if where_clauses:
            count_sql += " WHERE " + " AND ".join(where_clauses)
        count_row = conn.execute(count_sql, params).fetchone()
        total = count_row["cnt"] if count_row else 0

        offset = (page - 1) * per_page
        select_sql = """SELECT track_id, title, artist, release_year, genres, bpm,
                              peak_position, weeks_on_chart
                         FROM tracks"""
        if where_clauses:
            select_sql += " WHERE " + " AND ".join(where_clauses)
        select_sql += (
            " ORDER BY peak_position ASC, weeks_on_chart DESC LIMIT ? OFFSET ?"
        )
        rows = conn.execute(select_sql, params + [per_page, offset]).fetchall()

        results = []
        for row in rows:
            d = row_to_dict(row)
            d["genres"] = json.loads(d["genres"]) if d.get("genres") else []
            results.append(TrackSummary(**d))

        return CatalogPage(total=total, page=page, per_page=per_page, results=results)
    finally:
        conn.close()


@app.get("/tracks/{track_id}")
def get_track(track_id: str) -> Dict[str, Any]:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Track '{track_id}' not found")
        d = row_to_dict(row)
        for json_col in (
            "genres",
            "structure",
            "energy_curve",
            "instrumentation",
            "production_tags",
            "lyric_themes",
            "uniqueness_hooks",
        ):
            if d.get(json_col):
                try:
                    d[json_col] = json.loads(d[json_col])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
    finally:
        conn.close()


@app.get("/prompts/{track_id}")
def get_prompt_pack(track_id: str) -> Dict[str, Any]:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Track '{track_id}' not found")

        d = row_to_dict(row)
        for json_col in (
            "genres",
            "structure",
            "energy_curve",
            "instrumentation",
            "production_tags",
            "lyric_themes",
            "uniqueness_hooks",
        ):
            if d.get(json_col):
                try:
                    d[json_col] = json.loads(d[json_col])
                except (json.JSONDecodeError, TypeError):
                    pass

        dna = TrackDNA(**d)
        pack = export_prompt_pack_json(dna)

        # Attach lint results to each variation
        for variation in pack["variations"]:
            result = lint_prompt(
                style=variation["suno_style"],
                lyrics=variation["suno_lyrics"],
                instrumental=variation["instrumental"],
            )
            variation["lint"] = result.as_dict()

        return pack
    finally:
        conn.close()


@app.post("/lint", response_model=LintResponse)
def lint_on_demand(req: LintRequest) -> LintResponse:
    result = lint_prompt(
        style=req.style,
        lyrics=req.lyrics,
        instrumental=req.instrumental,
    )
    return LintResponse(**result.as_dict())


@app.get("/stats")
def catalog_stats() -> Dict[str, Any]:
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM tracks").fetchone()["cnt"]
        with_bpm = conn.execute(
            "SELECT COUNT(*) as cnt FROM tracks WHERE bpm IS NOT NULL"
        ).fetchone()["cnt"]
        with_dna = conn.execute(
            "SELECT COUNT(*) as cnt FROM tracks WHERE instrumentation IS NOT NULL"
        ).fetchone()["cnt"]
        year_range = conn.execute(
            "SELECT MIN(release_year) as yr_min, MAX(release_year) as yr_max FROM tracks"
        ).fetchone()

        return {
            "total_tracks": total,
            "tracks_with_bpm": with_bpm,
            "tracks_with_audio_dna": with_dna,
            "year_range": {
                "from": year_range["yr_min"],
                "to": year_range["yr_max"],
            },
        }
    finally:
        conn.close()


# ─── Dev entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.prompt_library:app", host="0.0.0.0", port=8000, reload=True)

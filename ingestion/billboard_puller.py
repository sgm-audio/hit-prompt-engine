"""
ingestion/billboard_puller.py

Fetches Billboard chart data across all in-scope charts from 1976–2026.
Two data sources:
  - HOT-100: Free GitHub JSON archive (mhollingshead/billboard-hot-100)
  - Genre charts: RapidAPI Billboard Charts API (paid, optional)
"""

import os
import httpx
import json
import sqlite3
import asyncio
from datetime import date, timedelta
from typing import Generator, Optional
from pathlib import Path

# ─── Data Sources ────────────────────────────────────────────────────────────

HOT100_BASE = (
    "https://raw.githubusercontent.com/mhollingshead/billboard-hot-100/main/date"
)
RAPIDAPI_HOST = "billboard-api2.p.rapidapi.com"

GENRE_CHARTS = [
    "hot-100",
    "r-b-hip-hop-songs",
    "country-songs",
    "pop-songs",
    "rock-songs",
    "latin-songs",
    "dance-electronic-songs",
    "rap-songs",
    "alternative-songs",
    "adult-contemporary",
    "gospel-songs",
    "reggae-songs",
    "k-pop",
    "afrobeats",
]

# ─── Week Generator ───────────────────────────────────────────────────────────


def week_generator(start: date, end: date) -> Generator[date, None, None]:
    """Generate every Saturday (Billboard chart date) between start and end."""
    current = start
    while current <= end:
        if current.weekday() == 5:  # Saturday
            yield current
        current += timedelta(days=1)


# ─── Fetchers ─────────────────────────────────────────────────────────────────


async def fetch_hot100_week(client: httpx.AsyncClient, chart_date: date) -> dict:
    """Pull one week of Hot-100 from free GitHub JSON archive."""
    url = f"{HOT100_BASE}/{chart_date.isoformat()}.json"
    r = await client.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


async def fetch_genre_chart(
    client: httpx.AsyncClient,
    chart: str,
    chart_date: date,
    api_key: str,
) -> dict:
    """Pull one genre chart week from RapidAPI Billboard."""
    url = f"https://{RAPIDAPI_HOST}/charts"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }
    params = {
        "chart": chart,
        "date": chart_date.isoformat(),
    }
    r = await client.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ─── Normalizer ───────────────────────────────────────────────────────────────


def normalize_hot100_entry(raw: dict, chart_date: date, chart_name: str) -> dict:
    """Normalize a chart entry to canonical schema."""
    return {
        "chart": chart_name,
        "chart_date": chart_date.isoformat(),
        "rank": raw.get("this_week"),
        "peak_position": raw.get("peak_position"),
        "weeks_on_chart": raw.get("weeks_on_chart"),
        "title": raw.get("song", "").strip(),
        "artist": raw.get("artist", "").strip(),
        "last_week": raw.get("last_week"),
    }


def normalize_rapidapi_entry(raw: dict, chart_date: date, chart_name: str) -> dict:
    """Normalize a RapidAPI genre chart entry to canonical schema."""
    return {
        "chart": chart_name,
        "chart_date": chart_date.isoformat(),
        "rank": raw.get("rank"),
        "peak_position": raw.get("peak_pos"),
        "weeks_on_chart": raw.get("weeks_on_chart"),
        "title": raw.get("title", "").strip(),
        "artist": raw.get("artist", "").strip(),
        "last_week": raw.get("last_week"),
    }


# ─── Main Ingestion Loop ──────────────────────────────────────────────────────


async def ingest_date_range(
    db_path: str,
    start_date: str,
    end_date: str,
    charts: list[str] | None = None,
    output_dir: str = "data/raw_charts",
):
    """Main ingestion loop — pulls all weeks across all charts and writes to DB."""
    from ingestion.deduper import upsert_track

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    chart_list = charts or ["hot-100"]
    api_key: Optional[str] = os.environ.get("RAPIDAPI_KEY")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    async with httpx.AsyncClient() as client:
        for week in week_generator(start, end):
            week_str = week.isoformat()
            out_file = Path(f"{output_dir}/{week_str}.json")

            if out_file.exists():
                print(f"[SKIP] {week_str} already cached")
                continue

            weekly_data: dict = {"date": week_str, "charts": {}}

            # Hot-100 (free)
            if "hot-100" in chart_list:
                try:
                    hot100 = await fetch_hot100_week(client, week)
                    entries = hot100.get("data", [])
                    for e in entries:
                        entry = normalize_hot100_entry(e, week, "hot-100")
                        upsert_track(
                            conn,
                            title=entry["title"],
                            artist=entry["artist"],
                            chart="hot-100",
                            chart_date=week_str,
                            rank=entry["rank"],
                            peak_position=entry["peak_position"],
                            weeks_on_chart=entry["weeks_on_chart"],
                        )
                    weekly_data["charts"]["hot-100"] = [
                        normalize_hot100_entry(e, week, "hot-100") for e in entries
                    ]
                except Exception as exc:
                    print(f"[WARN] Hot-100 failed for {week_str}: {exc}")

            # Genre charts (paid, optional)
            if api_key:
                for genre_chart in chart_list:
                    if genre_chart == "hot-100":
                        continue
                    try:
                        raw = await fetch_genre_chart(
                            client, genre_chart, week, api_key
                        )
                        entries = raw.get("content", raw.get("entries", []))
                        for entry_raw in entries:
                            entry = normalize_rapidapi_entry(
                                entry_raw, week, genre_chart
                            )
                            upsert_track(
                                conn,
                                title=entry["title"],
                                artist=entry["artist"],
                                chart=genre_chart,
                                chart_date=week_str,
                                rank=entry["rank"],
                                peak_position=entry["peak_position"],
                                weeks_on_chart=entry["weeks_on_chart"],
                            )
                        weekly_data["charts"][genre_chart] = [
                            normalize_rapidapi_entry(entry_raw, week, genre_chart)
                            for entry_raw in entries
                        ]
                        await asyncio.sleep(0.2)  # Respect rate limits
                    except Exception as exc:
                        print(f"[WARN] {genre_chart} failed for {week_str}: {exc}")

            # Save week (backup JSON)
            with open(out_file, "w") as f:
                json.dump(weekly_data, f, indent=2)
            print(f"[OK] Ingested {week_str}")

            await asyncio.sleep(0.1)  # Polite crawl pace

    conn.close()


if __name__ == "__main__":
    asyncio.run(
        ingest_date_range(
            db_path="hit_engine.db",
            start_date="1976-01-03",
            end_date="2026-03-15",
            charts=["hot-100"],
        )
    )

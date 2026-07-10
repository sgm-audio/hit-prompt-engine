"""
db/models.py

SQLAlchemy ORM models — production-grade upgrade path from raw SQLite.
Use this when migrating from direct sqlite3 calls to a managed schema.

Switch DB via DATABASE_URL env var:
  sqlite:///hit_engine.db        (default, dev)
  postgresql://user:pw@host/db   (production)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///hit_engine.db")

engine = create_engine(
    DATABASE_URL,
    # SQLite-specific: enable WAL for concurrent reads
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

# Enable WAL mode for SQLite
if "sqlite" in DATABASE_URL:

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


class Track(Base):
    """
    Core track record — populated by Phase 1 ingestion.
    DNA columns populated by Phase 2 audio analysis.
    """

    __tablename__ = "tracks"

    # ── Identity ────────────────────────────────────────────────────────────
    track_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    artist: Mapped[str] = mapped_column(String(255), nullable=False)
    release_year: Mapped[Optional[int]] = mapped_column(Integer)

    # ── External IDs ────────────────────────────────────────────────────────
    mbid: Mapped[Optional[str]] = mapped_column(String(36))  # MusicBrainz
    isrc: Mapped[Optional[str]] = mapped_column(String(12))
    spotify_id: Mapped[Optional[str]] = mapped_column(String(22))

    # ── Genre / tags (JSON arrays stored as text) ───────────────────────────
    genres: Mapped[Optional[str]] = mapped_column(Text)  # JSON list
    mb_genres: Mapped[Optional[str]] = mapped_column(Text)  # JSON list

    # ── Chart performance ────────────────────────────────────────────────────
    peak_position: Mapped[Optional[int]] = mapped_column(Integer)
    weeks_on_chart: Mapped[Optional[int]] = mapped_column(Integer)
    chart_source: Mapped[Optional[str]] = mapped_column(String(64))

    # ── Spotify audio features ───────────────────────────────────────────────
    bpm: Mapped[Optional[float]] = mapped_column(Float)
    key: Mapped[Optional[str]] = mapped_column(String(16))  # "F# minor"
    mode: Mapped[Optional[str]] = mapped_column(String(8))  # "major"|"minor"
    energy: Mapped[Optional[float]] = mapped_column(Float)
    valence: Mapped[Optional[float]] = mapped_column(Float)
    danceability: Mapped[Optional[float]] = mapped_column(Float)
    acousticness: Mapped[Optional[float]] = mapped_column(Float)
    instrumentalness: Mapped[Optional[float]] = mapped_column(Float)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Deep audio DNA (Phase 2 librosa + PANNs) ─────────────────────────────
    structure: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of sections
    energy_curve: Mapped[Optional[str]] = mapped_column(Text)  # JSON list[float] 10pt
    instrumentation: Mapped[Optional[str]] = mapped_column(Text)  # JSON list[str]
    production_tags: Mapped[Optional[str]] = mapped_column(Text)  # JSON list[str]
    vocal_profile: Mapped[Optional[str]] = mapped_column(String(32))

    # ── Safe inference (no actual lyrics) ────────────────────────────────────
    lyric_themes: Mapped[Optional[str]] = mapped_column(Text)  # JSON list[str]
    uniqueness_hooks: Mapped[Optional[str]] = mapped_column(Text)  # JSON list[str]

    # ── Meta ────────────────────────────────────────────────────────────────
    analysis_version: Mapped[str] = mapped_column(String(16), default="2.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Track {self.track_id} — {self.artist} '{self.title}'>"


class ChartEntry(Base):
    """One weekly chart placement for a track."""

    __tablename__ = "chart_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(String(32), nullable=False)
    chart_name: Mapped[str] = mapped_column(String(64), nullable=False)
    chart_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<ChartEntry {self.chart_name} {self.chart_date} #{self.position}>"


# ─── Schema management ────────────────────────────────────────────────────────


def create_all() -> None:
    """Create all tables. Safe to call multiple times."""
    Base.metadata.create_all(engine)


def get_session() -> Session:
    """Return a new ORM session."""
    return Session(engine)

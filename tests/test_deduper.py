"""
tests/test_deduper.py

Tests for ingestion/deduper.py
Covers: dedupe key normalization, fuzzy matching, upsert logic, DB schema.
"""

from ingestion.deduper import (
    make_dedupe_key,
    fuzzy_find_existing,
    upsert_track,
    init_db,
)


class TestDedupeKey:
    def test_basic_normalization(self):
        key = make_dedupe_key("Hello World", "Drake")
        assert "drake" in key
        assert "hello world" in key

    def test_removes_feat_parentheses(self):
        key1 = make_dedupe_key("God's Plan (feat. Nobody)", "Drake")
        key2 = make_dedupe_key("God's Plan", "Drake")
        assert key1 == key2

    def test_removes_remix_brackets(self):
        key1 = make_dedupe_key("Song [Explicit]", "Artist")
        key2 = make_dedupe_key("Song", "Artist")
        assert key1 == key2

    def test_removes_punctuation(self):
        key1 = make_dedupe_key("It's Now or Never!", "Elvis")
        key2 = make_dedupe_key("Its Now or Never", "Elvis")
        assert key1 == key2

    def test_case_insensitive(self):
        key1 = make_dedupe_key("SHAPE OF YOU", "ED SHEERAN")
        key2 = make_dedupe_key("shape of you", "ed sheeran")
        assert key1 == key2

    def test_format_is_artist_double_pipe_title(self):
        key = make_dedupe_key("Track Name", "Artist Name")
        assert "||" in key
        parts = key.split("||")
        assert len(parts) == 2
        assert parts[0] == "artist name"
        assert parts[1] == "track name"

    def test_extra_whitespace_normalized(self):
        key1 = make_dedupe_key("  Song  Title  ", "  My Artist  ")
        key2 = make_dedupe_key("Song Title", "My Artist")
        assert key1 == key2


class TestFuzzyFindExisting:
    def test_exact_match_found(self, temp_db):
        upsert_track(
            temp_db, "Shape of You", "Ed Sheeran", "hot-100", "2017-01-07", 1, 1, 12
        )
        result = fuzzy_find_existing(temp_db, "Shape of You", "Ed Sheeran")
        assert result is not None

    def test_feat_variant_matches(self, temp_db):
        upsert_track(
            temp_db, "Bad Guy", "Billie Eilish", "hot-100", "2019-03-29", 1, 1, 18
        )
        result = fuzzy_find_existing(temp_db, "Bad Guy (feat. Nobody)", "Billie Eilish")
        assert result is not None

    def test_no_match_returns_none(self, temp_db):
        upsert_track(
            temp_db, "Shape of You", "Ed Sheeran", "hot-100", "2017-01-07", 1, 1, 12
        )
        result = fuzzy_find_existing(
            temp_db, "Completely Different Song", "Random Artist"
        )
        assert result is None

    def test_empty_db_returns_none(self, temp_db):
        result = fuzzy_find_existing(temp_db, "Any Song", "Any Artist")
        assert result is None

    def test_high_threshold_prevents_false_positive(self, temp_db):
        upsert_track(temp_db, "Yellow", "Coldplay", "hot-100", "2000-07-01", 5, 5, 10)
        result = fuzzy_find_existing(temp_db, "Mellow", "Coldplay", threshold=99)
        # "yellow" vs "mellow" — should not match at 99%
        assert result is None


class TestUpsertTrack:
    def test_new_track_gets_id(self, temp_db):
        track_id = upsert_track(
            temp_db, "Test Song", "Test Artist", "hot-100", "2024-01-01", 1, 1, 10
        )
        assert track_id.startswith("trk_")
        assert len(track_id) > 4

    def test_track_stored_in_db(self, temp_db):
        track_id = upsert_track(
            temp_db, "Stored Song", "Artist A", "hot-100", "2024-01-01", 5, 5, 8
        )
        row = temp_db.execute(
            "SELECT * FROM tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        assert row is not None
        assert row["title"] == "Stored Song"

    def test_duplicate_track_not_duplicated(self, temp_db):
        upsert_track(
            temp_db, "Same Song", "Same Artist", "hot-100", "2024-01-01", 3, 3, 5
        )
        upsert_track(
            temp_db, "Same Song", "Same Artist", "hot-100", "2024-01-08", 2, 2, 6
        )
        count = temp_db.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        assert count == 1

    def test_chart_entries_logged_for_each_insert(self, temp_db):
        track_id = upsert_track(
            temp_db, "Chart Song", "Artist", "hot-100", "2024-01-01", 5, 5, 4
        )
        upsert_track(temp_db, "Chart Song", "Artist", "hot-100", "2024-01-08", 4, 4, 5)
        entries = temp_db.execute(
            "SELECT * FROM chart_entries WHERE track_id = ?", (track_id,)
        ).fetchall()
        assert len(entries) == 2

    def test_peak_position_updated_on_duplicate(self, temp_db):
        track_id = upsert_track(
            temp_db, "Peak Song", "Artist", "hot-100", "2024-01-01", 10, 10, 3
        )
        upsert_track(temp_db, "Peak Song", "Artist", "hot-100", "2024-01-08", 1, 1, 4)
        row = temp_db.execute(
            "SELECT peak_hot100 FROM tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        assert row["peak_hot100"] == 1  # Should take the better peak

    def test_deterministic_track_id(self, temp_db):
        """Same artist+title → same MD5 hash → same track_id."""
        id1 = upsert_track(
            temp_db, "Consistent", "Artist", "hot-100", "2024-01-01", 1, 1, 1
        )
        # Insert different track first to populate DB
        upsert_track(
            temp_db, "Other Track", "Other Artist", "hot-100", "2024-01-01", 2, 2, 1
        )
        # Now re-compute expected ID
        import hashlib

        raw = "artist|consistent"
        expected_id = (
            "trk_" + hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
        )
        assert id1 == expected_id

    def test_release_year_stored(self, temp_db):
        track_id = upsert_track(
            temp_db,
            "Old Song",
            "Classic Artist",
            "hot-100",
            "1985-06-01",
            3,
            3,
            12,
            release_year=1985,
        )
        row = temp_db.execute(
            "SELECT release_year FROM tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        assert row["release_year"] == 1985

    def test_isrc_stored(self, temp_db):
        track_id = upsert_track(
            temp_db,
            "ISRC Song",
            "Artist",
            "hot-100",
            "2024-01-01",
            1,
            1,
            1,
            isrc="USUM71900001",
        )
        row = temp_db.execute(
            "SELECT isrc FROM tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        assert row["isrc"] == "USUM71900001"


class TestInitDb:
    def test_creates_tracks_table(self, temp_db):
        tables = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "tracks" in table_names

    def test_creates_chart_entries_table(self, temp_db):
        tables = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "chart_entries" in table_names

    def test_idempotent_init(self):
        """Calling init_db twice should not raise."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            c1 = init_db(path)
            c1.execute("PRAGMA journal_mode=DELETE")
            c1.close()
            c2 = init_db(path)  # Second call — should be a no-op
            c2.execute("PRAGMA journal_mode=DELETE")
            c2.close()
        finally:
            for suffix in ("", "-wal", "-shm"):
                try:
                    os.unlink(path + suffix)
                except FileNotFoundError:
                    pass

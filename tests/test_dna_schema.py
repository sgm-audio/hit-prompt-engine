"""
tests/test_dna_schema.py

Tests for dna/dna_schema.py
Covers: computed helpers, field validation, defaults.
"""

import pytest
from dna.dna_schema import TrackDNA


class TestEnergyLabel:
    @pytest.mark.parametrize(
        "energy,expected",
        [
            (0.9, "peak"),
            (0.8, "peak"),
            (0.75, "high"),
            (0.6, "high"),
            (0.5, "mid"),
            (0.35, "mid"),
            (0.34, "low"),
            (0.0, "low"),
        ],
    )
    def test_energy_thresholds(self, energy, expected):
        dna = TrackDNA(
            track_id="x",
            title="T",
            artist="A",
            release_year=2020,
            genres=["pop"],
            energy=energy,
        )
        assert dna.energy_label() == expected

    def test_none_energy_returns_mid(self):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=2020, genres=["pop"]
        )
        assert dna.energy_label() == "mid"


class TestBpmInt:
    def test_rounds_up(self):
        dna = TrackDNA(
            track_id="x",
            title="T",
            artist="A",
            release_year=2020,
            genres=["pop"],
            bpm=135.7,
        )
        assert dna.bpm_int() == 136

    def test_rounds_down(self):
        dna = TrackDNA(
            track_id="x",
            title="T",
            artist="A",
            release_year=2020,
            genres=["pop"],
            bpm=135.2,
        )
        assert dna.bpm_int() == 135

    def test_none_bpm_returns_none(self):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=2020, genres=["pop"]
        )
        assert dna.bpm_int() is None

    def test_integer_bpm_unchanged(self):
        dna = TrackDNA(
            track_id="x",
            title="T",
            artist="A",
            release_year=2020,
            genres=["pop"],
            bpm=120.0,
        )
        assert dna.bpm_int() == 120


class TestEra:
    @pytest.mark.parametrize(
        "year,expected",
        [
            (1976, "1970s"),
            (1979, "1970s"),
            (1980, "1980s"),
            (1989, "1980s"),
            (1990, "1990s"),
            (1999, "1990s"),
            (2000, "2000s"),
            (2009, "2000s"),
            (2010, "2010s"),
            (2019, "2010s"),
            (2020, "2020s"),
            (2023, "2020s"),
            (2024, "2026"),
            (2026, "2026"),
        ],
    )
    def test_era_for_year(self, year, expected):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=year, genres=["pop"]
        )
        assert dna.era() == expected


class TestDefaults:
    def test_default_structure(self):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=2020, genres=["pop"]
        )
        assert "verse" in dna.structure
        assert "chorus" in dna.structure

    def test_default_analysis_version(self):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=2020, genres=["pop"]
        )
        assert dna.analysis_version == "2.0"

    def test_optional_fields_default_none(self):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=2020, genres=["pop"]
        )
        assert dna.bpm is None
        assert dna.key is None
        assert dna.mbid is None

    def test_list_fields_default_empty(self):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=2020, genres=["pop"]
        )
        assert dna.instrumentation == []
        assert dna.production_tags == []
        assert dna.lyric_themes == []


class TestValidation:
    def test_required_fields_must_be_present(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TrackDNA(title="T", artist="A", release_year=2020)  # Missing track_id

    def test_genres_can_be_empty_list(self):
        dna = TrackDNA(
            track_id="x", title="T", artist="A", release_year=2020, genres=[]
        )
        assert dna.genres == []

    def test_full_dna_roundtrip(self, full_dna):
        """Serialization → deserialization should be lossless."""
        d = full_dna.model_dump()
        restored = TrackDNA(**d)
        assert restored.track_id == full_dna.track_id
        assert restored.bpm == full_dna.bpm
        assert restored.lyric_themes == full_dna.lyric_themes

"""
tests/test_genre_normalizer.py

Tests for enrichment/genre_normalizer.py
"""

import pytest
from enrichment.genre_normalizer import normalize_genre, normalize_genres


class TestNormalizeGenre:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("hip hop", "hip_hop"),
            ("hip-hop", "hip_hop"),
            ("rap", "hip_hop"),
            ("trap", "hip_hop"),
            ("drill", "hip_hop"),
            ("boom bap", "hip_hop"),
            ("r&b", "rnb"),
            ("rnb", "rnb"),
            ("soul", "rnb"),
            ("neo-soul", "rnb"),
            ("funk", "rnb"),
            ("pop", "pop"),
            ("dance pop", "electronic"),  # dance → electronic
            ("edm", "electronic"),
            ("house", "electronic"),
            ("techno", "electronic"),
            ("country", "country"),
            ("country pop", "country"),
            ("rock", "rock"),
            ("classic rock", "rock"),
            ("alternative", "alternative"),
            ("indie rock", "alternative"),
            ("grunge", "alternative"),
            ("folk", "folk"),
            ("americana", "folk"),
            ("jazz", "jazz"),
            ("smooth jazz", "jazz"),
            ("gospel", "gospel"),
            ("christian", "gospel"),
            ("reggae", "reggae"),
            ("dancehall", "reggae"),
            ("k-pop", "kpop"),
            ("kpop", "kpop"),
            ("afrobeats", "afrobeats"),
            ("amapiano", "afrobeats"),
            ("latin", "latin"),
            ("reggaeton", "latin"),
            ("metal", "metal"),
            ("heavy metal", "metal"),
            ("metalcore", "metal"),
        ],
    )
    def test_known_genre(self, raw, expected):
        assert normalize_genre(raw) == expected

    def test_unknown_genre_defaults_to_pop(self):
        assert normalize_genre("xyzzy music") == "pop"

    def test_case_insensitive(self):
        assert normalize_genre("HIP HOP") == "hip_hop"
        assert normalize_genre("R&B") == "rnb"

    def test_extra_whitespace_handled(self):
        assert normalize_genre("  pop  ") == "pop"


class TestNormalizeGenres:
    def test_deduplicates_genres(self):
        result = normalize_genres(["hip hop", "rap", "trap"])
        assert result.count("hip_hop") == 1

    def test_preserves_order_of_first_occurrence(self):
        result = normalize_genres(["pop", "rock", "alternative"])
        assert result[0] == "pop"
        assert result[1] == "rock"

    def test_empty_list_fallback_to_pop(self):
        result = normalize_genres([])
        assert result == ["pop"]

    def test_all_unknown_fallback_to_pop(self):
        result = normalize_genres(["xyzzy", "foobar"])
        assert result == ["pop"]

    def test_mixed_known_unknown(self):
        result = normalize_genres(["pop", "xyzzy"])
        assert "pop" in result

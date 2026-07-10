"""
tests/test_theme_extractor.py

Tests for dna/theme_extractor.py
Verifies: title keyword inference, acoustic feature mapping, genre modifiers,
deduplication, max_themes cap, fallback behavior.
"""

from dna.theme_extractor import infer_themes


class TestTitleKeywords:
    def test_love_in_title_yields_romance(self):
        themes = infer_themes("Love Story", ["pop"])
        assert "romance" in themes

    def test_night_in_title_yields_nightlife(self):
        themes = infer_themes("Friday Night", ["pop"])
        assert "nightlife" in themes

    def test_sad_in_title_yields_heartbreak(self):
        themes = infer_themes("Sad Eyes", ["pop"])
        assert "heartbreak" in themes

    def test_money_in_title_yields_hustle(self):
        themes = infer_themes("Money Rain", ["hip_hop"])
        assert "hustle" in themes

    def test_god_in_title_yields_spirituality(self):
        themes = infer_themes("God's Plan", ["gospel"])
        assert "spirituality" in themes

    def test_summer_in_title_yields_nostalgia(self):
        themes = infer_themes("Summer Days", ["pop"])
        assert "nostalgia" in themes

    def test_fire_in_title_yields_energy(self):
        themes = infer_themes("Fire & Ice", ["rock"])
        assert "energy" in themes

    def test_rebel_in_title_yields_rebellion(self):
        themes = infer_themes("Rebel Soul", ["alternative"])
        assert "rebellion" in themes

    def test_city_in_title_yields_journey(self):
        themes = infer_themes("City Lights", ["r&b"])
        assert "journey" in themes

    def test_case_insensitive(self):
        themes = infer_themes("LOVE YOU FOREVER", ["pop"])
        assert "romance" in themes

    def test_no_match_returns_fallback(self):
        themes = infer_themes("Zxqvbmk Track", [])
        assert themes == ["emotion", "storytelling"]


class TestAcousticFeatures:
    def test_high_valence_high_energy_yields_confidence(self):
        themes = infer_themes("Track", ["pop"], valence=0.8, energy=0.85)
        assert themes[0] == "confidence"  # Acoustic inference gets priority

    def test_low_valence_low_energy_yields_heartbreak(self):
        themes = infer_themes("Track", ["pop"], valence=0.3, energy=0.4)
        assert "heartbreak" in themes

    def test_low_valence_high_energy_yields_tension(self):
        themes = infer_themes("Track", ["pop"], valence=0.35, energy=0.7)
        assert "tension" in themes

    def test_mid_valence_low_energy_yields_romance(self):
        themes = infer_themes("Track", ["pop"], valence=0.55, energy=0.35)
        assert "romance" in themes

    def test_acoustic_overrides_title_keyword(self):
        """Acoustic inference should bubble to front via insert(0, ...)."""
        themes = infer_themes("Love Song", ["pop"], valence=0.8, energy=0.85)
        assert themes[0] == "confidence"  # Not romance from title


class TestGenreModifiers:
    def test_country_adds_nostalgia_journey(self):
        themes = infer_themes("Open Road", ["country"])
        assert "nostalgia" in themes or "journey" in themes

    def test_hip_hop_adds_hustle_triumph(self):
        themes = infer_themes("Unknown Track", ["hip_hop"])
        assert "hustle" in themes or "triumph" in themes

    def test_gospel_adds_spirituality(self):
        themes = infer_themes("Unknown Track", ["gospel"])
        assert "spirituality" in themes

    def test_electronic_adds_nightlife_energy(self):
        themes = infer_themes("Unknown Track", ["electronic"])
        assert "nightlife" in themes or "energy" in themes

    def test_metal_adds_rebellion(self):
        themes = infer_themes("Unknown Track", ["metal"])
        assert "rebellion" in themes


class TestDeduplication:
    def test_no_duplicate_themes(self):
        themes = infer_themes("Love Night City", ["hip_hop", "rnb"])
        assert len(themes) == len(set(themes))

    def test_theme_appears_only_once(self):
        # Both title and genre might suggest "hustle"
        themes = infer_themes("Money Grind", ["hip_hop"])
        assert themes.count("hustle") == 1


class TestMaxThemes:
    def test_default_max_is_3(self):
        themes = infer_themes(
            "Love Night Fire Rebel City", ["hip_hop", "country", "electronic"]
        )
        assert len(themes) <= 3

    def test_custom_max_themes(self):
        themes = infer_themes("Love Night Fire", ["hip_hop"], max_themes=5)
        assert len(themes) <= 5

    def test_max_1_returns_single_theme(self):
        themes = infer_themes("Love Song", ["pop"], max_themes=1)
        assert len(themes) == 1


class TestFallback:
    def test_empty_title_empty_genres_fallback(self):
        themes = infer_themes("", [])
        assert themes == ["emotion", "storytelling"]

    def test_none_acoustic_features_handled(self):
        """Should not raise when valence/energy are None."""
        themes = infer_themes("Track", ["pop"], valence=None, energy=None)
        assert isinstance(themes, list)

    def test_partial_acoustic_features_handled(self):
        """valence without energy shouldn't crash."""
        themes = infer_themes("Track", ["pop"], valence=0.7, energy=None)
        assert isinstance(themes, list)

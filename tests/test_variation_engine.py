"""
tests/test_variation_engine.py

Tests for prompt_compiler/variation_engine.py
Covers: 6-pack generation, BPM deltas, JSON export structure, lint integration.
"""

from prompt_compiler.variation_engine import (
    generate_prompt_pack,
    export_prompt_pack_json,
    VARIATION_RECIPES,
    PromptPack,
)
from prompt_compiler.prompt_linter import lint_prompt


class TestVariationRecipes:
    def test_exactly_6_recipes(self):
        assert len(VARIATION_RECIPES) == 6

    def test_recipe_ids_unique(self):
        ids = [r["id"] for r in VARIATION_RECIPES]
        assert len(ids) == len(set(ids))

    def test_required_recipe_keys(self):
        required = {
            "id",
            "name",
            "intent",
            "style_mod",
            "lyrics_mod",
            "instrumental",
            "bpm_delta",
        }
        for recipe in VARIATION_RECIPES:
            assert required.issubset(recipe.keys()), (
                f"Recipe {recipe.get('id')} missing keys: {required - recipe.keys()}"
            )

    def test_exactly_one_instrumental_recipe(self):
        instrumental = [r for r in VARIATION_RECIPES if r["instrumental"]]
        assert len(instrumental) == 1
        assert instrumental[0]["id"] == "V5_instrumental"

    def test_v1_has_zero_bpm_delta(self):
        v1 = next(r for r in VARIATION_RECIPES if r["id"] == "V1_faithful")
        assert v1["bpm_delta"] == 0

    def test_v6_has_positive_bpm_delta(self):
        v6 = next(r for r in VARIATION_RECIPES if r["id"] == "V6_club_remix")
        assert v6["bpm_delta"] > 0


class TestGeneratePromptPack:
    def test_returns_6_packs(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        assert len(packs) == 6

    def test_all_packs_are_prompt_pack_instances(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        assert all(isinstance(p, PromptPack) for p in packs)

    def test_track_id_preserved(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        assert all(p.track_id == full_dna.track_id for p in packs)

    def test_style_strings_not_empty(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        assert all(p.style.strip() for p in packs)

    def test_lyrics_strings_not_empty(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for p in packs:
            assert p.lyrics.strip(), f"Empty lyrics for {p.variation_id}"

    def test_instrumental_pack_has_no_lyrics(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        instrumental = next(p for p in packs if p.instrumental)
        assert (
            "no lyrics" in instrumental.lyrics.lower()
            or "instrumental" in instrumental.lyrics.lower()
        )

    def test_bpm_delta_applied_to_club_remix(self, full_dna):
        """V6 club remix should have BPM = base + 10, capped at 160."""
        packs = generate_prompt_pack(full_dna)
        v6 = next(p for p in packs if p.variation_id == "V6_club_remix")
        # full_dna.bpm = 135.2 → v6 BPM should be 145
        assert v6.settings.get("bpm") == 145

    def test_bpm_delta_not_applied_to_v1(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        v1 = next(p for p in packs if p.variation_id == "V1_faithful")
        assert v1.settings.get("bpm") == full_dna.bpm_int()

    def test_stripped_bpm_reduced(self, full_dna):
        """V4 stripped should lower BPM by 8."""
        packs = generate_prompt_pack(full_dna)
        v4 = next(p for p in packs if p.variation_id == "V4_stripped")
        expected_bpm = max(60, int(round(full_dna.bpm - 8)))
        assert v4.settings.get("bpm") == expected_bpm

    def test_bpm_floor_at_60(self):
        """BPM should never drop below 60."""
        from dna.dna_schema import TrackDNA

        slow_dna = TrackDNA(
            track_id="slow",
            title="Slow",
            artist="X",
            release_year=2020,
            genres=["folk"],
            bpm=62.0,
        )
        packs = generate_prompt_pack(slow_dna)
        v4 = next(p for p in packs if p.variation_id == "V4_stripped")
        assert v4.settings.get("bpm") >= 60

    def test_instrumental_vocal_profile_is_none(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        instrumental = next(p for p in packs if p.instrumental)
        assert instrumental.settings.get("vocal_profile") is None

    def test_non_instrumental_vocal_profile_present(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        non_instrumental = [p for p in packs if not p.instrumental]
        for p in non_instrumental:
            # vocal_profile from full_dna = "female_pop"
            assert p.settings.get("vocal_profile") == "female_pop"

    def test_variation_ids_match_recipes(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        recipe_ids = {r["id"] for r in VARIATION_RECIPES}
        pack_ids = {p.variation_id for p in packs}
        assert pack_ids == recipe_ids

    def test_minimal_dna_still_generates_6_packs(self, minimal_dna):
        packs = generate_prompt_pack(minimal_dna)
        assert len(packs) == 6


class TestExportJSON:
    def test_export_returns_dict(self, full_dna):
        result = export_prompt_pack_json(full_dna)
        assert isinstance(result, dict)

    def test_export_top_level_keys(self, full_dna):
        result = export_prompt_pack_json(full_dna)
        required = {
            "track_id",
            "source_title",
            "source_artist",
            "source_year",
            "primary_genre",
            "analysis_version",
            "variations",
        }
        assert required.issubset(result.keys())

    def test_export_6_variations(self, full_dna):
        result = export_prompt_pack_json(full_dna)
        assert len(result["variations"]) == 6

    def test_export_variation_keys(self, full_dna):
        result = export_prompt_pack_json(full_dna)
        required = {
            "id",
            "name",
            "intent",
            "suno_style",
            "suno_lyrics",
            "instrumental",
            "settings",
            "lint",
        }
        for v in result["variations"]:
            assert required.issubset(v.keys()), (
                f"Variation {v.get('id')} missing: {required - v.keys()}"
            )

    def test_source_artist_is_preserved(self, full_dna):
        result = export_prompt_pack_json(full_dna)
        assert result["source_artist"] == full_dna.artist

    def test_primary_genre_fallback_to_pop(self, minimal_dna):
        minimal_dna.genres = []
        result = export_prompt_pack_json(minimal_dna)
        assert result["primary_genre"] == "pop"


class TestLintIntegration:
    def test_all_variations_lintable(self, full_dna):
        """Every generated pack should be lintable without exceptions."""
        packs = generate_prompt_pack(full_dna)
        for p in packs:
            result = lint_prompt(p.style, p.lyrics, instrumental=p.instrumental)
            assert isinstance(result.score, float)
            assert 0.0 <= result.score <= 1.0

    def test_majority_of_packs_pass_lint(self, full_dna):
        """At least 4/6 variations should pass the linter."""
        packs = generate_prompt_pack(full_dna)
        passing = sum(
            1
            for p in packs
            if lint_prompt(p.style, p.lyrics, instrumental=p.instrumental).passed
        )
        assert passing >= 4, f"Only {passing}/6 variations passed linting"

    def test_style_field_under_char_limit_in_all_packs(self, full_dna):
        from prompt_compiler.style_builder import STYLE_CHAR_LIMIT

        packs = generate_prompt_pack(full_dna)
        for p in packs:
            assert len(p.style) <= STYLE_CHAR_LIMIT, (
                f"Style too long in {p.variation_id}: {len(p.style)} chars"
            )

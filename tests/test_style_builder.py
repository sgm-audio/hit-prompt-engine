"""
tests/test_style_builder.py

Tests for prompt_compiler/style_builder.py
Covers: char limit, genre-first ordering, variation modes, BPM injection, no artist names.
"""

from prompt_compiler.style_builder import build_style_prompt, STYLE_CHAR_LIMIT


class TestCharLimit:
    def test_output_never_exceeds_200_chars(self, full_dna):
        for variation in [
            "faithful",
            "modern_2026",
            "genre_bent",
            "stripped",
            "instrumental",
            "club_remix",
        ]:
            result = build_style_prompt(full_dna, variation=variation)
            assert len(result) <= STYLE_CHAR_LIMIT, (
                f"Variation '{variation}' exceeded 200 chars: {len(result)}"
            )

    def test_output_not_empty(self, minimal_dna):
        result = build_style_prompt(minimal_dna)
        assert result.strip() != ""

    def test_no_trailing_comma(self, full_dna):
        for variation in ["faithful", "modern_2026", "stripped", "club_remix"]:
            result = build_style_prompt(full_dna, variation=variation)
            assert not result.strip().endswith(","), (
                f"Variation '{variation}' ends with comma"
            )


class TestGenreFirst:
    def test_genre_is_first_tag_faithful(self, full_dna):
        result = build_style_prompt(full_dna, variation="faithful")
        first_tag = result.split(",")[0].strip().lower()
        assert "pop" in first_tag or "electronic" in first_tag

    def test_genre_is_first_tag_hip_hop(self, hip_hop_dna):
        result = build_style_prompt(hip_hop_dna, variation="faithful")
        first_tag = result.split(",")[0].strip().lower()
        assert "hip" in first_tag or "hop" in first_tag

    def test_genre_is_first_tag_acoustic(self, acoustic_dna):
        result = build_style_prompt(acoustic_dna, variation="faithful")
        # Folk → "folk acoustic"
        assert result.lower().startswith("folk") or result.lower().startswith(
            "acoustic"
        )


class TestBPMInjection:
    def test_bpm_in_faithful_when_present(self, full_dna):
        result = build_style_prompt(full_dna, variation="faithful")
        assert "BPM" in result
        assert "135" in result  # bpm=135.2 → 135

    def test_no_bpm_when_none(self, minimal_dna):
        # minimal_dna has bpm=None
        result = build_style_prompt(minimal_dna, variation="faithful")
        assert "BPM" not in result

    def test_club_remix_bpm_capped_at_160(self, full_dna):
        # full_dna.bpm = 135.2, +10 = 145.2 → 145
        result = build_style_prompt(full_dna, variation="club_remix")
        assert "145 BPM" in result

    def test_club_remix_bpm_at_very_high_bpm_capped(self):
        """Club remix should never exceed 160 BPM."""
        from dna.dna_schema import TrackDNA

        fast_dna = TrackDNA(
            track_id="fast",
            title="Fast",
            artist="X",
            release_year=2020,
            genres=["electronic"],
            bpm=160.0,
        )
        result = build_style_prompt(fast_dna, variation="club_remix")
        assert "160 BPM" in result
        assert "170 BPM" not in result


class TestVariations:
    def test_faithful_contains_energy_label(self, full_dna):
        result = build_style_prompt(full_dna, variation="faithful")
        # energy=0.82 → "peak" or "high"
        assert any(
            label in result.lower() for label in ["peak", "high", "energy", "anthemic"]
        )

    def test_modern_2026_contains_2026(self, full_dna):
        result = build_style_prompt(full_dna, variation="modern_2026")
        assert "2026" in result

    def test_stripped_contains_acoustic(self, full_dna):
        result = build_style_prompt(full_dna, variation="stripped")
        assert "acoustic" in result.lower() or "stripped" in result.lower()

    def test_stripped_bpm_reduced(self, full_dna):
        # full_dna.bpm=135 → stripped BPM = max(60, 135-8) = 127
        result = build_style_prompt(full_dna, variation="stripped")
        assert "127 BPM" in result

    def test_instrumental_contains_no_vocals(self, full_dna):
        result = build_style_prompt(full_dna, variation="instrumental")
        assert "no vocals" in result.lower() or "instrumental" in result.lower()

    def test_instrumental_contains_sync_ready(self, full_dna):
        result = build_style_prompt(full_dna, variation="instrumental")
        assert "sync" in result.lower()

    def test_club_remix_contains_four_on_floor(self, full_dna):
        result = build_style_prompt(full_dna, variation="club_remix")
        assert "four-on-the-floor" in result.lower()

    def test_genre_bent_contains_cross_genre(self, full_dna):
        # genre_bent mixes primary genre with a random alt genre
        result = build_style_prompt(full_dna, variation="genre_bent")
        assert "pop" in result.lower() or "influenced" in result.lower()


class TestNoCopyrightContent:
    def test_no_artist_names_in_any_variation(self, full_dna):
        """Style field must never contain artist names."""
        from prompt_compiler.prompt_linter import BLOCKED_ARTIST_TERMS

        for variation in [
            "faithful",
            "modern_2026",
            "genre_bent",
            "stripped",
            "instrumental",
            "club_remix",
        ]:
            result = build_style_prompt(full_dna, variation=variation).lower()
            for artist in BLOCKED_ARTIST_TERMS:
                assert artist not in result, (
                    f"Artist '{artist}' found in {variation} style: {result}"
                )


class TestEraProduction:
    def test_eighties_era_in_faithful(self, eighties_dna):
        result = build_style_prompt(eighties_dna, variation="faithful")
        # ERA_PRODUCTION_MAP["1980s"] → "gated reverb drums"
        assert "gated" in result.lower() or "reverb" in result.lower()

    def test_era_derivation(self):
        from dna.dna_schema import TrackDNA

        for year, expected_era in [
            (1978, "1970s"),
            (1985, "1980s"),
            (1995, "1990s"),
            (2005, "2000s"),
            (2015, "2010s"),
            (2022, "2020s"),
        ]:
            dna = TrackDNA(
                track_id="x", title="T", artist="A", release_year=year, genres=["pop"]
            )
            assert dna.era() == expected_era

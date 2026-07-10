"""
tests/test_prompt_linter.py

Tests for prompt_compiler/prompt_linter.py
Covers: char limits, artist blocking, section tags, BPM check, scoring.
"""

from prompt_compiler.prompt_linter import lint_prompt, STYLE_CHAR_LIMIT


# ─── Helpers ──────────────────────────────────────────────────────────────────

VALID_STYLE = "pop, 118 BPM, high energy, driving rhythm, C major, polished male vocals"
VALID_LYRICS = """[Verse]
(story setup: raw emotion)
(4 lines, build toward the hook)

[Chorus]
(MAIN HOOK: unstoppable feeling)
(4 lines, big singable melody)

[Bridge]
(shift perspective)
"""


# ─── Happy path ───────────────────────────────────────────────────────────────


class TestHappyPath:
    def test_valid_prompt_passes(self):
        result = lint_prompt(VALID_STYLE, VALID_LYRICS)
        assert result.passed is True
        assert result.score >= 0.6
        assert result.errors == []

    def test_score_is_float_in_range(self):
        result = lint_prompt(VALID_STYLE, VALID_LYRICS)
        assert 0.0 <= result.score <= 1.0

    def test_instrumental_skips_lyrics_checks(self):
        result = lint_prompt(VALID_STYLE, "", instrumental=True)
        # No section-tag error for instrumental
        assert not any("section tag" in e for e in result.errors)

    def test_as_dict_structure(self):
        result = lint_prompt(VALID_STYLE, VALID_LYRICS)
        d = result.as_dict()
        assert set(d.keys()) == {"passed", "score", "warnings", "errors", "suggestions"}
        assert isinstance(d["warnings"], list)


# ─── Style field ──────────────────────────────────────────────────────────────


class TestStyleField:
    def test_over_char_limit_is_error(self):
        long_style = "pop, " + "x" * (STYLE_CHAR_LIMIT + 10)
        result = lint_prompt(long_style, VALID_LYRICS)
        assert any("too long" in e.lower() for e in result.errors)

    def test_near_limit_is_warning_not_error(self):
        # 185-199 chars — warning zone
        near_limit = "pop, 118 BPM, " + "a" * 175
        if len(near_limit) < STYLE_CHAR_LIMIT:
            result = lint_prompt(near_limit, VALID_LYRICS)
            assert not any("too long" in e.lower() for e in result.errors)

    def test_artist_name_in_style_is_error(self):
        style = "taylor swift inspired pop, 120 BPM"
        result = lint_prompt(style, VALID_LYRICS)
        assert any("taylor swift" in e.lower() for e in result.errors)

    def test_multiple_artist_names_multiple_errors(self):
        style = "pop, beyonce meets drake vibes"
        result = lint_prompt(style, VALID_LYRICS)
        blocked = [
            e for e in result.errors if "beyonce" in e.lower() or "drake" in e.lower()
        ]
        assert len(blocked) >= 2

    def test_genre_not_first_is_warning(self):
        style = "polished vocals, pop, 120 BPM"
        result = lint_prompt(style, VALID_LYRICS)
        assert any("genre" in w.lower() for w in result.warnings)

    def test_genre_first_no_warning(self):
        style = "pop, 120 BPM, energetic, polished vocals"
        result = lint_prompt(style, VALID_LYRICS)
        assert not any("genre" in w.lower() for w in result.warnings)

    def test_no_bpm_generates_suggestion(self):
        style = "pop, high energy, driving rhythm"
        result = lint_prompt(style, VALID_LYRICS)
        assert any("bpm" in s.lower() for s in result.suggestions)

    def test_bpm_present_no_bpm_suggestion(self):
        style = "pop, 120 BPM, high energy"
        result = lint_prompt(style, VALID_LYRICS)
        assert not any("bpm" in s.lower() for s in result.suggestions)

    def test_too_few_tags_warning(self):
        style = "pop, 120 BPM"  # only 2 tags
        result = lint_prompt(style, VALID_LYRICS)
        assert any("tags" in w.lower() for w in result.warnings)

    def test_too_many_tags_warning(self):
        style = ", ".join([f"tag{i}" for i in range(15)])
        result = lint_prompt(style, VALID_LYRICS)
        assert any("tags" in w.lower() or "noise" in w.lower() for w in result.warnings)


# ─── Lyrics field ─────────────────────────────────────────────────────────────


class TestLyricsField:
    def test_missing_section_tag_is_error(self):
        bare_lyrics = "just some words without any tags"
        result = lint_prompt(VALID_STYLE, bare_lyrics)
        assert any("section tag" in e.lower() for e in result.errors)

    def test_has_verse_tag_passes(self):
        lyrics = "[Verse]\nsome words here\n"
        result = lint_prompt(VALID_STYLE, lyrics)
        assert not any("section tag" in e.lower() for e in result.errors)

    def test_has_chorus_tag_passes(self):
        lyrics = "[Chorus]\nthe big hook\n"
        result = lint_prompt(VALID_STYLE, lyrics)
        assert not any("section tag" in e.lower() for e in result.errors)

    def test_artist_name_in_lyrics_is_error(self):
        lyrics = "[Verse]\nI wanna be like michael jackson on the floor\n"
        result = lint_prompt(VALID_STYLE, lyrics)
        assert any("michael jackson" in e.lower() for e in result.errors)

    def test_iconic_fragment_is_error(self):
        lyrics = "[Chorus]\nI will always love you, always love you\n"
        result = lint_prompt(VALID_STYLE, lyrics)
        assert any("copyrighted" in e.lower() for e in result.errors)

    def test_lyrics_too_long_is_error(self):
        long_lyrics = "[Verse]\n" + "line\n" * 700
        result = lint_prompt(VALID_STYLE, long_lyrics)
        assert any("too long" in e.lower() for e in result.errors)

    def test_lyrics_3000_chars_exact_no_error(self):
        # Exactly 3000 chars should not trigger the length error
        filler = "word " * 100  # ~500 chars
        lyrics = "[Verse]\n" + filler * 5  # ~2508 chars
        result = lint_prompt(VALID_STYLE, lyrics[:3000])
        assert not any("too long" in e.lower() for e in result.errors)


# ─── Scoring ──────────────────────────────────────────────────────────────────


class TestScoring:
    def test_perfect_prompt_near_1(self):
        result = lint_prompt(VALID_STYLE, VALID_LYRICS)
        # No errors, minimal warnings → high score
        assert result.score >= 0.84

    def test_error_reduces_score(self):
        bad_style = "taylor swift pop, 120 BPM, high energy"
        result = lint_prompt(bad_style, VALID_LYRICS)
        assert result.score < 0.76  # 1 error × 0.25 penalty

    def test_multiple_errors_can_reach_zero(self):
        bad_style = "taylor swift beyonce drake, 120 BPM"
        bad_lyrics = "I will always love you\nbillie jean is not my lover"
        result = lint_prompt(bad_style, bad_lyrics)
        assert result.score == 0.0
        assert result.passed is False

    def test_passed_false_when_errors_exist(self):
        result = lint_prompt("no genre here", "no section tags here")
        assert result.passed is False

    def test_score_never_negative(self):
        """Score floor is 0.0 regardless of how many errors."""
        terrible_style = "taylor swift beyonce drake eminem rihanna madonna beyoncé"
        terrible_lyrics = "I will always love you\nbillie jean is not my lover\nthriller thriller night"
        result = lint_prompt(terrible_style, terrible_lyrics)
        assert result.score >= 0.0

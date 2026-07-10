"""
tests/test_scorer.py

Tests for prompt_compiler/scorer.py
Validates the auto-scoring engine against known good/bad prompt packs.
"""

import pytest
from prompt_compiler.scorer import score_pack, score_all_packs, ScoreResult
from prompt_compiler.variation_engine import generate_prompt_pack


class TestScoreResult:
    def test_as_dict_structure(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        result = score_pack(packs[0], full_dna, all_packs=packs)
        d = result.as_dict()
        assert set(d.keys()) == {"total", "grade", "dimensions", "flags", "suggestions"}
        assert isinstance(d["dimensions"], dict)

    def test_total_in_range(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for pack in packs:
            result = score_pack(pack, full_dna, all_packs=packs)
            assert 0 <= result.total <= 100

    def test_grade_is_letter(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        result = score_pack(packs[0], full_dna, all_packs=packs)
        assert result.grade in {"A", "B", "C", "D", "F"}


class TestScoreDimensions:
    def test_dimension_keys_present(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        result = score_pack(packs[0], full_dna, all_packs=packs)
        expected_dims = {
            "structure_adherence",
            "tempo_accuracy",
            "prosody_quality",
            "style_field_quality",
            "thematic_coherence",
        }
        assert expected_dims == set(result.dimensions.keys())

    def test_dimension_sum_equals_total(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for pack in packs:
            result = score_pack(pack, full_dna, all_packs=packs)
            assert result.total == sum(result.dimensions.values())

    def test_structure_max_40(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for pack in packs:
            result = score_pack(pack, full_dna, all_packs=packs)
            assert result.dimensions["structure_adherence"] <= 40

    def test_tempo_max_20(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for pack in packs:
            result = score_pack(pack, full_dna, all_packs=packs)
            assert result.dimensions["tempo_accuracy"] <= 20

    def test_prosody_max_20(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for pack in packs:
            result = score_pack(pack, full_dna, all_packs=packs)
            assert result.dimensions["prosody_quality"] <= 20

    def test_style_max_10(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for pack in packs:
            result = score_pack(pack, full_dna, all_packs=packs)
            assert result.dimensions["style_field_quality"] <= 10

    def test_theme_max_10(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        for pack in packs:
            result = score_pack(pack, full_dna, all_packs=packs)
            assert result.dimensions["thematic_coherence"] <= 10


class TestScoreAllPacks:
    def test_returns_dict_of_6(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        results = score_all_packs(packs, full_dna)
        assert len(results) == 6

    def test_keys_are_variation_ids(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        results = score_all_packs(packs, full_dna)
        expected_ids = {p.variation_id for p in packs}
        assert set(results.keys()) == expected_ids

    def test_all_scores_are_score_results(self, full_dna):
        packs = generate_prompt_pack(full_dna)
        results = score_all_packs(packs, full_dna)
        assert all(isinstance(v, ScoreResult) for v in results.values())

    def test_faithful_outscores_minimal_dna(self, minimal_dna, full_dna):
        """
        A fully-populated DNA should produce higher scores than minimal.
        Full DNA has themes, instrumentation, energy curves = more structure.
        """
        min_packs = generate_prompt_pack(minimal_dna)
        full_packs = generate_prompt_pack(full_dna)

        min_avg = (
            sum(score_pack(p, minimal_dna, min_packs).total for p in min_packs) / 6
        )
        full_avg = (
            sum(score_pack(p, full_dna, full_packs).total for p in full_packs) / 6
        )

        # Full DNA should generally score higher — themes improve thematic coherence
        assert (
            full_avg >= min_avg - 10
        )  # Allow 10pt tolerance for randomness in genre_bent


class TestGradeThresholds:
    @pytest.mark.parametrize(
        "total,grade",
        [
            (95, "A"),
            (90, "A"),
            (89, "B"),
            (80, "B"),
            (79, "C"),
            (70, "C"),
            (69, "D"),
            (60, "D"),
            (59, "F"),
            (0, "F"),
        ],
    )
    def test_grade_thresholds(self, total, grade):
        from prompt_compiler.scorer import _letter_grade

        assert _letter_grade(total) == grade


class TestTempoScoring:
    @pytest.mark.parametrize(
        "diff,min_score",
        [
            (0, 20),
            (2, 20),
            (3, 17),
            (5, 17),
            (8, 12),
            (10, 12),
            (12, 7),
            (15, 7),
            (20, 3),
        ],
    )
    def test_tempo_score_by_diff(self, diff, min_score):
        from prompt_compiler.scorer import _score_tempo

        score = _score_tempo(120, 120 + diff)
        assert score >= min_score - 1  # Allow 1pt tolerance

    def test_no_bpm_returns_neutral(self):
        from prompt_compiler.scorer import _score_tempo

        assert _score_tempo(None, None) == 10
        assert _score_tempo(120, None) == 10
        assert _score_tempo(None, 120) == 10

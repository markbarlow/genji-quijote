"""Unit tests for pipeline/pair_scorer.py.

Tests pair scoring and mode classification using actual weight values
from config/scoring_weights.json.
"""

import json
import pathlib

from pipeline.pair_scorer import score_pair


# ---------------------------------------------------------------------------
# Load actual weights from config so test assertions use real values
# ---------------------------------------------------------------------------

_WEIGHTS_PATH = pathlib.Path(__file__).parents[2] / "config" / "scoring_weights.json"
with _WEIGHTS_PATH.open() as _f:
    _ALL_WEIGHTS = json.load(_f)

PAIR_WEIGHTS = _ALL_WEIGHTS["pair"]

ENCOUNTER_BONUS = PAIR_WEIGHTS["character_encounter_bonus"]
NAMED_BONUS = PAIR_WEIGHTS["character_named_bonus"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_score_pair_returns_tuple():
    """score_pair must return a (float, str) tuple."""
    result = score_pair(0.5, 0.5, [], [], PAIR_WEIGHTS)
    assert isinstance(result, tuple)
    assert len(result) == 2
    pair_score, mode = result
    assert isinstance(pair_score, float)
    assert isinstance(mode, str)


def test_score_pair_mode_character_encounter():
    """Both halves having characters yields mode 'character_encounter'."""
    _, mode = score_pair(0.5, 0.5, ["Genji"], ["Don_Quixote"], PAIR_WEIGHTS)
    assert mode == "character_encounter"


def test_score_pair_mode_character_named_genji_only():
    """Only the Genji half having characters yields mode 'character_named'."""
    _, mode = score_pair(0.5, 0.5, ["Genji"], [], PAIR_WEIGHTS)
    assert mode == "character_named"


def test_score_pair_mode_character_named_quijote_only():
    """Only the Quijote half having characters yields mode 'character_named'."""
    _, mode = score_pair(0.5, 0.5, [], ["Don_Quixote"], PAIR_WEIGHTS)
    assert mode == "character_named"


def test_score_pair_mode_standard():
    """Neither half having characters yields mode 'standard'."""
    _, mode = score_pair(0.5, 0.5, [], [], PAIR_WEIGHTS)
    assert mode == "standard"


def test_score_pair_encounter_bonus_applied():
    """An encounter pair scores higher than a standard pair with identical base scores."""
    base_genji = 0.6
    base_quijote = 0.6

    encounter_score, _ = score_pair(
        base_genji, base_quijote, ["Genji"], ["Don_Quixote"], PAIR_WEIGHTS
    )
    standard_score, _ = score_pair(base_genji, base_quijote, [], [], PAIR_WEIGHTS)

    expected_diff = ENCOUNTER_BONUS
    actual_diff = encounter_score - standard_score

    assert abs(actual_diff - expected_diff) < 1e-9, (
        f"Encounter bonus should be exactly {expected_diff}, got diff={actual_diff}"
    )
    assert encounter_score > standard_score


def test_score_pair_named_bonus_applied():
    """A named pair scores higher than a standard pair with identical base scores."""
    base_genji = 0.4
    base_quijote = 0.4

    named_score, _ = score_pair(base_genji, base_quijote, ["Genji"], [], PAIR_WEIGHTS)
    standard_score, _ = score_pair(base_genji, base_quijote, [], [], PAIR_WEIGHTS)

    expected_diff = NAMED_BONUS
    actual_diff = named_score - standard_score

    assert abs(actual_diff - expected_diff) < 1e-9, (
        f"Named bonus should be exactly {expected_diff}, got diff={actual_diff}"
    )
    assert named_score > standard_score


def test_score_pair_base_is_average():
    """With no characters, pair score equals the simple average of the two sentence scores."""
    genji_score = 0.3
    quijote_score = 0.7

    pair_score, mode = score_pair(genji_score, quijote_score, [], [], PAIR_WEIGHTS)

    expected_base = (genji_score + quijote_score) / 2
    assert mode == "standard"
    assert abs(pair_score - expected_base) < 1e-9, (
        f"Expected {expected_base}, got {pair_score}"
    )

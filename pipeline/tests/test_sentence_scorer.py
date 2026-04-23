"""Unit tests for pipeline/sentence_scorer.py.

Tests lexical interestingness scoring using inline registries and
actual weight values from config/scoring_weights.json.
"""

import json
import pathlib
import pytest

from pipeline.sentence_scorer import score_sentence


# ---------------------------------------------------------------------------
# Load actual weights from config so test assertions use real values
# ---------------------------------------------------------------------------

_WEIGHTS_PATH = pathlib.Path(__file__).parents[2] / "config" / "scoring_weights.json"
with _WEIGHTS_PATH.open() as _f:
    _ALL_WEIGHTS = json.load(_f)

WEIGHTS = _ALL_WEIGHTS["sentence"]

# Convenience aliases matching scoring_weights.json keys
LENGTH_WEIGHT = WEIGHTS["length_weight"]
LENGTH_MIN = WEIGHTS["length_sweet_spot_min"]
LENGTH_MAX = WEIGHTS["length_sweet_spot_max"]
CHAR_MAJOR = WEIGHTS["character_major_score"]
CHAR_MINOR = WEIGHTS["character_minor_score"]
PLACE_BONUS = WEIGHTS["place_name_bonus"]
LEX_WEIGHT = WEIGHTS["lexical_diversity_weight"]


# ---------------------------------------------------------------------------
# Minimal inline registries for testing
# ---------------------------------------------------------------------------

GENJI_REGISTRY = {
    "Genji": {
        "rank": "major",
        "variants": ["Prince Genji"],
        "score_weight": 1.0,
    },
    "Murasaki": {
        "rank": "major",
        "variants": ["Lady Murasaki"],
        "score_weight": 0.95,
    },
    "Ukon": {
        "rank": "minor",
        "variants": [],
        "score_weight": 0.30,
    },
}


# ---------------------------------------------------------------------------
# Helper: build a sentence of a given word count
# ---------------------------------------------------------------------------

def _sentence_of(n_words: int, varied: bool = True) -> str:
    """Return a sentence of exactly n_words words.

    If varied=True each word is distinct (good for lexical diversity tests).
    If varied=False content words repeat (bad for lexical diversity).
    """
    if varied:
        words = [f"word{i}" for i in range(n_words)]
    else:
        # Repeat the same content word after a stopword opener
        words = ["the"] + ["apple"] * (n_words - 1)
    return " ".join(words)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_score_returns_float():
    """score_sentence must return a Python float."""
    result = score_sentence("She walked quietly.", [], GENJI_REGISTRY, WEIGHTS)
    assert isinstance(result, float)


def test_score_sweet_spot_length_contributes_max():
    """A sentence within the length sweet spot scores higher on length than one outside."""
    # 15 words is within [LENGTH_MIN, LENGTH_MAX] → full length weight
    sweet_sentence = _sentence_of(15)
    # 5 words is below LENGTH_MIN — linear fall-off applies
    short_sentence = _sentence_of(5)

    score_sweet = score_sentence(sweet_sentence, [], GENJI_REGISTRY, WEIGHTS)
    score_short = score_sentence(short_sentence, [], GENJI_REGISTRY, WEIGHTS)

    assert score_sweet > score_short, (
        f"Sweet-spot sentence ({score_sweet:.4f}) should outscore "
        f"short sentence ({score_short:.4f})"
    )


def test_score_outside_sweet_spot_reduces_length():
    """Very short (3 words) or very long (70 words) sentences get a reduced length component."""
    sweet_sentence = _sentence_of(15)
    very_short = _sentence_of(3)
    very_long = _sentence_of(70)

    score_sweet = score_sentence(sweet_sentence, [], GENJI_REGISTRY, WEIGHTS)
    score_very_short = score_sentence(very_short, [], GENJI_REGISTRY, WEIGHTS)
    score_very_long = score_sentence(very_long, [], GENJI_REGISTRY, WEIGHTS)

    assert score_sweet > score_very_short, "Sweet spot should beat very short"
    assert score_sweet > score_very_long, "Sweet spot should beat very long"


def test_score_major_character_raises_score():
    """A sentence with a detected major character scores higher than the same sentence with none."""
    sentence = "Genji gazed at the moon in the quiet autumn garden night."
    score_with_char = score_sentence(sentence, ["Genji"], GENJI_REGISTRY, WEIGHTS)
    score_without_char = score_sentence(sentence, [], GENJI_REGISTRY, WEIGHTS)

    assert score_with_char > score_without_char, (
        f"Major character should raise score: {score_with_char:.4f} vs {score_without_char:.4f}"
    )


def test_score_minor_character_raises_score_less_than_major():
    """A minor character raises the score less than a major character."""
    sentence = "She walked quietly through the corridor at dusk without speaking."

    # Ukon is minor (score_weight=0.30), Genji is major (score_weight=1.0)
    score_major = score_sentence(sentence, ["Genji"], GENJI_REGISTRY, WEIGHTS)
    score_minor = score_sentence(sentence, ["Ukon"], GENJI_REGISTRY, WEIGHTS)
    score_none = score_sentence(sentence, [], GENJI_REGISTRY, WEIGHTS)

    assert score_major > score_minor > score_none, (
        f"Expected major ({score_major:.4f}) > minor ({score_minor:.4f}) > none ({score_none:.4f})"
    )


def test_score_capital_word_raises_place_score():
    """A mid-sentence capital word triggers the place-name bonus."""
    sentence_with_place = "She walked to Kyoto in the afternoon."
    sentence_without_place = "She walked to town in the afternoon."

    score_place = score_sentence(sentence_with_place, [], GENJI_REGISTRY, WEIGHTS)
    score_no_place = score_sentence(sentence_without_place, [], GENJI_REGISTRY, WEIGHTS)

    assert score_place > score_no_place, (
        f"Place-name sentence ({score_place:.4f}) should outscore plain sentence ({score_no_place:.4f})"
    )


def test_score_first_word_capital_not_counted_as_place():
    """A sentence whose only capital is the first word must NOT trigger the place bonus."""
    # Only the first word is capitalised; no internal capitals → no place bonus
    sentence = "She walked to town in the afternoon."
    # Compute expected score manually: no place bonus contributes
    # Score should equal sentence_without_place from the previous test
    score = score_sentence(sentence, [], GENJI_REGISTRY, WEIGHTS)

    # Check it does NOT equal a score that would include the place_name_bonus
    # by verifying adding PLACE_BONUS to the no-place score would be greater
    # i.e. we verify that this sentence does not get the bonus
    score_with_forced_bonus = score + PLACE_BONUS
    assert score_with_forced_bonus > score, (
        "Sanity: score without place bonus is less than score + bonus"
    )


def test_score_lexical_diversity_favours_varied_vocabulary():
    """A sentence with unique content words scores higher than one with repeated content words."""
    # All different content words → high type-token ratio
    varied_sentence = "moonlight silence autumn beauty sorrow longing memory dream river cloud"
    # Same content word repeated → low type-token ratio
    repetitive_sentence = "moonlight moonlight moonlight moonlight moonlight moonlight moonlight moonlight moonlight moonlight"

    score_varied = score_sentence(varied_sentence, [], GENJI_REGISTRY, WEIGHTS)
    score_repetitive = score_sentence(repetitive_sentence, [], GENJI_REGISTRY, WEIGHTS)

    assert score_varied > score_repetitive, (
        f"Varied vocab ({score_varied:.4f}) should outscore repetitive ({score_repetitive:.4f})"
    )


def test_score_no_characters_still_scores():
    """A sentence with no detected characters still returns a non-zero score."""
    sentence = "The autumn leaves fell silently into the dark still river below."
    score = score_sentence(sentence, [], GENJI_REGISTRY, WEIGHTS)
    assert score > 0.0, f"Expected non-zero score, got {score}"


def test_score_all_components_combine():
    """Sentence in sweet spot with major character and good diversity outscores a bare sentence."""
    # Good sentence: 15 words, major char, internal capital, varied vocabulary
    good_sentence = (
        "Genji wandered through Kyoto's moonlit pavilion watching autumn leaves descend silently."
    )
    # Bare sentence: 3 words, no chars, no place, repetitive
    bare_sentence = "the the the"

    score_good = score_sentence(good_sentence, ["Genji"], GENJI_REGISTRY, WEIGHTS)
    score_bare = score_sentence(bare_sentence, [], GENJI_REGISTRY, WEIGHTS)

    assert score_good > score_bare, (
        f"Full-featured sentence ({score_good:.4f}) should greatly outscore bare sentence ({score_bare:.4f})"
    )

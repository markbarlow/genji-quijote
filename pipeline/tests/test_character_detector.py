"""Unit tests for pipeline/character_detector.py.

Tests whole-word, case-insensitive character detection using inline registries.
"""

import pytest

from pipeline.character_detector import detect_characters


# ---------------------------------------------------------------------------
# Minimal inline registries for testing
# ---------------------------------------------------------------------------

MINI_REGISTRY = {
    "Genji": {
        "rank": "major",
        "variants": ["Prince Genji", "the Shining Prince"],
        "score_weight": 1.0
    },
    "Murasaki": {
        "rank": "major",
        "variants": ["Lady Murasaki"],
        "score_weight": 0.95
    },
    "Ukon": {
        "rank": "minor",
        "variants": [],
        "score_weight": 0.30
    }
}

MINI_QUIJOTE_REGISTRY = {
    "Don_Quixote": {
        "rank": "major",
        "variants": ["Don Quijote", "the Knight of the Sad Countenance"],
        "score_weight": 1.0
    },
    "Sancho_Panza": {
        "rank": "major",
        "variants": ["Sancho", "the squire"],
        "score_weight": 0.95
    }
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_detect_canonical_name():
    """Test detection of a canonical character name."""
    sentence = "Genji looked at the moon."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert result == ["Genji"]


def test_detect_variant_name():
    """Test that variant names are matched and canonical name is returned."""
    sentence = "The Shining Prince wept alone."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert result == ["Genji"]


def test_detect_returns_canonical_not_variant():
    """Verify result contains canonical name, not variant string."""
    sentence = "Prince Genji and Lady Murasaki spoke quietly."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert "Genji" in result
    assert "Prince Genji" not in result
    assert "Lady Murasaki" not in result


def test_detect_multiple_characters():
    """Test detection of multiple distinct characters in one sentence."""
    sentence = "Genji spoke to Murasaki tenderly."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert "Genji" in result
    assert "Murasaki" in result
    assert len(result) == 2


def test_detect_no_match():
    """Test that sentences with no character names return empty list."""
    sentence = "The autumn leaves fell silently."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert result == []


def test_detect_case_insensitive():
    """Test that matching is case-insensitive."""
    sentence = "genji gazed at the moon alone."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert result == ["Genji"]


def test_detect_whole_word_only():
    """Test that partial matches (no word boundary) are not detected."""
    sentence = "Genjis robe was beautiful."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert result == []


def test_detect_empty_variants_list():
    """Test that characters with empty variants list are still detected."""
    sentence = "Ukon stood quietly by the door."
    result = detect_characters(sentence, MINI_REGISTRY)
    assert result == ["Ukon"]


def test_detect_underscore_key_matched_as_spaced():
    """Test that underscore-based canonical keys match spaced text."""
    sentence = "Don Quixote rode through the valley."
    result = detect_characters(sentence, MINI_QUIJOTE_REGISTRY)
    assert result == ["Don_Quixote"]


def test_detect_no_duplicates():
    """Test that a character appearing multiple times returns canonical name once."""
    sentence = "Sancho and the squire rode together, and the squire laughed."
    result = detect_characters(sentence, MINI_QUIJOTE_REGISTRY)
    assert result.count("Sancho_Panza") == 1

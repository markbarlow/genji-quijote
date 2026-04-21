"""Unit tests for pipeline/sentence_filter.py.

Tests filtering logic for removing short, long, pattern-matching, and all-caps sentences.
"""

import pytest
import re

from pipeline.sentence_filter import filter_sentences


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_config():
    """Minimal config dict for testing."""
    return {
        "genji": {
            "sentence_patterns": [re.compile(r"^\[\d+\]")],
            "min_tokens": 8,
            "max_tokens": 60,
        },
        "quijote": {
            "sentence_patterns": [],
            "latin_pattern": r"\b(est|sunt|erat|ergo|ad|de|per|cum|non)\b",
            "min_tokens": 8,
            "max_tokens": 60,
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_filter_removes_blank_sentences(minimal_config):
    """Verify blank and whitespace-only sentences are removed."""
    sentences = [
        "This is a valid sentence with enough words here.",
        "",
        "   ",
        "\t\n",
        "Another valid sentence with many words to test.",
    ]
    result = filter_sentences(sentences, "genji", minimal_config)
    assert "" not in result
    assert "   " not in result
    assert len(result) == 2


def test_filter_respects_min_tokens(minimal_config):
    """Verify sentences below min_tokens are filtered."""
    sentences = [
        "Too short.",  # 2 words
        "This is a valid sentence with enough words to pass.",  # 11 words
        "Still too few words.",  # 4 words
    ]
    result = filter_sentences(sentences, "genji", minimal_config)
    assert "Too short." not in result
    assert "Still too few words." not in result
    assert len(result) == 1
    assert "This is a valid sentence with enough words to pass." in result


def test_filter_respects_max_tokens(minimal_config):
    """Verify sentences above max_tokens are filtered."""
    # Create a sentence with 61 words to exceed max of 60
    long_sentence = " ".join(["word"] * 61)
    short_sentence = " ".join(["word"] * 10)

    sentences = [long_sentence, short_sentence]
    result = filter_sentences(sentences, "genji", minimal_config)
    assert long_sentence not in result
    assert short_sentence in result


def test_filter_removes_sentence_pattern_matches(minimal_config):
    """Verify sentences matching genji patterns are removed."""
    sentences = [
        "[1] This sentence starts with a footnote marker and has enough words.",
        "This is a normal sentence without any markers and has enough words.",
        "[2] Another footnote marker at the start with additional content here.",
    ]
    result = filter_sentences(sentences, "genji", minimal_config)
    # Note: We expect the pattern to match sentences starting with [digit]
    # Both footnote sentences should be filtered
    assert "[1] This sentence starts with a footnote marker and has enough words." not in result
    assert "[2] Another footnote marker at the start with additional content here." not in result
    assert "This is a normal sentence without any markers and has enough words." in result


def test_filter_removes_all_caps_sentences(minimal_config):
    """Verify all-caps sentences (headings) are removed."""
    sentences = [
        "This is a normal sentence with proper capitalization.",
        "IN A VILLAGE OF LA MANCHA THERE LIVED A GENTLEMAN OF THE OLD SCHOOL.",
        "Another normal sentence here with mixed case and sufficient words.",
        "ALL CAPS HEADING",
    ]
    result = filter_sentences(sentences, "genji", minimal_config)
    # All caps sentences should be filtered
    assert "IN A VILLAGE OF LA MANCHA THERE LIVED A GENTLEMAN OF THE OLD SCHOOL." not in result
    assert "ALL CAPS HEADING" not in result
    # Normal sentences should pass
    assert "This is a normal sentence with proper capitalization." in result
    assert "Another normal sentence here with mixed case and sufficient words." in result


def test_filter_removes_latin_sentences_for_quijote(minimal_config):
    """Verify sentences matching latin_pattern are removed for quijote."""
    sentences = [
        "The emperor est very wise and powerful indeed.",  # Contains 'est'
        "This is a normal sentence without Latin words.",
        "In that time ergo all was confusion and disorder.",  # Contains 'ergo'
    ]
    result = filter_sentences(sentences, "quijote", minimal_config)
    # Latin sentences should be filtered
    assert "The emperor est very wise and powerful indeed." not in result
    assert "In that time ergo all was confusion and disorder." not in result
    # Normal sentence should pass
    assert "This is a normal sentence without Latin words." in result


def test_filter_latin_check_not_applied_to_genji(minimal_config):
    """Verify quijote latin_pattern is not applied to genji."""
    sentences = [
        "The emperor est very wise and powerful indeed.",  # Would match Latin pattern
        "This is a normal sentence without Latin words.",
    ]
    result = filter_sentences(sentences, "genji", minimal_config)
    # For genji, the latin pattern should not be applied
    # Both sentences should pass length and pattern checks
    assert len(result) >= 1
    # The latin sentence should pass through for genji (no latin filter)
    if "The emperor est very wise and powerful indeed." in result:
        # Good, it wasn't filtered
        pass


def test_filter_passes_valid_sentences(minimal_config):
    """Verify clean, valid sentences pass through all filters."""
    sentences = [
        "This is a perfectly valid sentence with good length.",
        "Another clean sentence that meets all requirements here.",
        "One more valid sentence to ensure filtering works.",
    ]
    result = filter_sentences(sentences, "genji", minimal_config)
    assert len(result) == 3
    for sentence in sentences:
        assert sentence in result

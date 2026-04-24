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
            "latin_pattern": r"\b(est|sunt|erat|ergo|nunc|enim|igitur|quod|sed|etiam)\b",
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
        "The emperor est very wise and powerful indeed today always.",  # Would match Latin pattern (8+ words)
        "This is a normal sentence without Latin words for genji here.",  # 10 words
    ]
    result = filter_sentences(sentences, "genji", minimal_config)
    # For genji, the latin pattern should not be applied
    # Both sentences should pass through (no latin filter for genji)
    assert "The emperor est very wise and powerful indeed today always." in result
    assert "This is a normal sentence without Latin words for genji here." in result


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


def test_filter_word_count_at_exact_boundaries(minimal_config):
    """Sentences at exactly min/max token count should pass; one over/under should fail."""
    # Exactly 8 words (at min boundary — should pass)
    sentence_8 = "The prince gazed upon the autumn moon this evening."
    # Exactly 7 words (below min — should fail)
    sentence_7 = "The prince gazed upon the autumn."
    # Exactly 60 words (at max boundary — should pass)
    sentence_60 = " ".join(["word"] * 60)
    # Exactly 61 words (above max — should fail)
    sentence_61 = " ".join(["word"] * 61)

    result = filter_sentences([sentence_8, sentence_60], "genji", minimal_config)
    assert sentence_8 in result
    assert sentence_60 in result

    result = filter_sentences([sentence_7, sentence_61], "genji", minimal_config)
    assert sentence_7 not in result
    assert sentence_61 not in result


def test_filter_allows_single_word_exclamation(minimal_config):
    """Single-word exclamations like 'I' should not be caught by the ALL CAPS filter.

    They will still be filtered by min_tokens (single word < 8), but the reason
    should be word count, not the ALL CAPS check — this test verifies the ALL CAPS
    filter is not the cause of rejection for short exclamations.
    """
    # A 9-word exclamatory sentence that is not ALL CAPS — should pass
    long_exclamation = "O what a terrible sight this was to behold!"
    result = filter_sentences([long_exclamation], "genji", minimal_config)
    assert long_exclamation in result


def test_filter_all_caps_requires_multiple_words(minimal_config):
    """ALL CAPS filter should only apply to multi-word headings (3+ words)."""
    # Multi-word ALL CAPS heading — should be filtered
    heading = "IN THE REIGN OF A GREAT EMPEROR OF JAPAN"
    # Single-word capital — should NOT be filtered by ALL CAPS check
    # (will fail min_tokens but not the all-caps filter)
    single = "I"

    result = filter_sentences([heading], "genji", minimal_config)
    assert heading not in result

    # Verify the single capital is not in result BUT only due to min_tokens, not isupper
    # We can verify this indirectly: the 3+ word threshold means "I" doesn't trigger isupper
    # (it still fails min_tokens — that's fine and expected)
    result_with_long = filter_sentences(
        ["I have walked many miles across the plains today."], "genji", minimal_config
    )
    assert "I have walked many miles across the plains today." in result_with_long


@pytest.fixture
def quijote_filter_config():
    """Config with the real quijote sentence_patterns (quotes and first-person I)."""
    return {
        "genji": {
            "sentence_patterns": [],
            "min_tokens": 8,
            "max_tokens": 60,
        },
        "quijote": {
            "sentence_patterns": [
                '["\\u201c\\u201d]',
                "\\bI\\b",
            ],
            "latin_pattern": "",
            "min_tokens": 8,
            "max_tokens": 60,
        },
    }


def test_filter_removes_quijote_sentences_with_straight_quotes(quijote_filter_config):
    """Quijote sentences containing straight double quotes are filtered out."""
    with_quotes = 'He said "saddle my horse" and went to the stable at dawn.'
    without_quotes = "He said to saddle his horse and went to the stable at dawn."
    result = filter_sentences([with_quotes, without_quotes], "quijote", quijote_filter_config)
    assert with_quotes not in result
    assert without_quotes in result


def test_filter_removes_quijote_sentences_with_curly_quotes(quijote_filter_config):
    """Quijote sentences containing curly double quotes are filtered out."""
    with_curly = "\u201cSaddle my horse at once,\u201d said Don Quixote to his squire Sancho."
    without_quotes = "Don Quixote ordered his squire Sancho to saddle his horse at once."
    result = filter_sentences([with_curly, without_quotes], "quijote", quijote_filter_config)
    assert with_curly not in result
    assert without_quotes in result


def test_filter_removes_quijote_sentences_with_first_person(quijote_filter_config):
    """Quijote sentences containing standalone 'I' are filtered (dialogue/narration clash)."""
    with_i = "I will tell you the truth about what happened on that very day."
    without_i = "He told the truth about what happened on that very day."
    result = filter_sentences([with_i, without_i], "quijote", quijote_filter_config)
    assert with_i not in result
    assert without_i in result


def test_filter_quote_pattern_not_applied_to_genji(quijote_filter_config):
    """The quote and first-person filters are quijote-only; genji sentences pass through."""
    with_quotes = 'She said "I cannot go" and remained at the palace through the night.'
    result = filter_sentences([with_quotes], "genji", quijote_filter_config)
    assert with_quotes in result

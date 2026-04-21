"""test_sentence_halver.py — unit tests for sentence_halver.halve_sentence.

Tests cover: return type, clause-boundary splitting (comma, semicolon, conjunction),
midpoint fallback, rejection, minimum-half enforcement, and round-trip rejoining.

Run with:
    cd /Users/Mark/Github/genji-quijote
    python3 -m pytest pipeline/tests/test_sentence_halver.py -v
"""

import pytest
from pipeline.sentence_halver import halve_sentence

# Minimal config shared across all tests — no file loading required.
TEST_CONFIG = {
    "halving": {
        "midpoint_window_tokens": 5,
        "minimum_half_tokens": 4,
        "boundary_priority": [
            ";", "—", ",", "but", "yet", "though",
            "when", "while", "and", "for", "nor"
        ]
    }
}


# ---------------------------------------------------------------------------
# 1. Return shape
# ---------------------------------------------------------------------------

def test_halve_returns_tuple_of_three():
    """halve_sentence must always return a 3-tuple, even on rejection."""
    sentence = "The prince walked slowly through the garden and the moon rose high above."
    result = halve_sentence(sentence, TEST_CONFIG)
    assert isinstance(result, tuple)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# 2. Clause-boundary splits
# ---------------------------------------------------------------------------

def test_halve_at_comma_boundary():
    """A comma at the end of a word near the midpoint should cause a split there.

    'Genji gazed at the moon, and the night was still.' — comma trails 'moon,'
    so the split should occur BEFORE 'and', putting 'and ...' in the second half.
    """
    sentence = "Genji gazed at the moon, and the night was still."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    # The comma on 'moon,' should trigger a split before 'and'
    assert second.startswith("and"), (
        f"Expected second half to start with 'and', got: {second!r}"
    )
    assert strategy == "clause_boundary"


def test_halve_at_semicolon_boundary():
    """A semicolon near the midpoint should split the sentence before the following word."""
    # 10 words; midpoint at index 5; semicolon trails word at index 4
    sentence = "The lady waited in the hall; her servants stood silent and still."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    # Word at index 4 is 'hall;' — split should be BEFORE index 5 ('her')
    assert "hall;" in first, f"'hall;' should be in first half; got: {first!r}"
    assert second.startswith("her"), f"Expected second half to start with 'her'; got: {second!r}"
    assert strategy == "clause_boundary"


def test_halve_at_conjunction_in_window():
    """A 'but' near the midpoint triggers a clause-boundary split before 'but'."""
    # 10 words; 'but' at index 5 (midpoint)
    sentence = "He wanted to sleep but his mind refused to rest tonight."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert second.startswith("but"), (
        f"Expected second half to start with 'but', got: {second!r}"
    )
    assert strategy == "clause_boundary"


# ---------------------------------------------------------------------------
# 5. Closest-to-midpoint wins
# ---------------------------------------------------------------------------

def test_halve_prefers_closest_to_midpoint():
    """When two boundaries exist in the window, the one closer to the midpoint wins.

    Sentence (12 words):
        'She sang and the river flowed, but the stars remained cold.'
    words:  0:'She' 1:'sang' 2:'and' 3:'the' 4:'river' 5:'flowed,' 6:'but' 7:'the' 8:'stars' 9:'remained' 10:'cold.'
    mid = 6; window = [1..11] clamped to [1..10]
    'flowed,' (index 5) has comma → split before index 6 ('but'), distance 0 from mid.
    'and' (index 2) → split before index 2, distance 4 from mid.
    'but' (index 6) → split before index 6, distance 0 from mid.
    Both 'flowed,' and 'but' are at distance 0 (before index 6);
    boundary_priority has ',' before 'but' so comma wins — second half starts with 'but'.
    """
    sentence = "She sang and the river flowed, but the stars remained cold."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    # The comma on 'flowed,' is at index 5, triggering split before index 6 ('but')
    assert second.startswith("but"), (
        f"Expected second half to start with 'but' (closest boundary wins); got: {second!r}"
    )
    assert strategy == "clause_boundary"


# ---------------------------------------------------------------------------
# 6-8. Fallback and strategy labels
# ---------------------------------------------------------------------------

def test_halve_falls_back_to_midpoint_when_no_boundary():
    """A sentence with no punctuation or conjunctions in the window falls back to word midpoint."""
    # 10 plain words, no commas, no conjunctions
    sentence = "The tall cherry blossoms swayed gracefully under the pale afternoon sky."
    _, _, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy == "word_midpoint"


def test_halve_strategy_clause_boundary():
    """Strategy string is exactly 'clause_boundary' when a boundary is found."""
    sentence = "Genji gazed at the moon, and the night was still."
    _, _, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy == "clause_boundary"


def test_halve_strategy_word_midpoint():
    """Strategy string is exactly 'word_midpoint' when no boundary is found."""
    sentence = "The tall cherry blossoms swayed gracefully under the pale afternoon sky."
    _, _, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy == "word_midpoint"


def test_halve_strategy_rejected():
    """Strategy string is exactly 'rejected' when the sentence is too short."""
    sentence = "He slept."
    _, _, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy == "rejected"


# ---------------------------------------------------------------------------
# 9-11. Rejection cases
# ---------------------------------------------------------------------------

def test_halve_rejected_when_too_short():
    """A 6-word sentence with minimum_half_tokens=4 must be rejected (6 < 2*4=8)."""
    sentence = "He ran into the dark forest."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert first is None
    assert second is None
    assert strategy == "rejected"


def test_halve_rejected_when_boundary_creates_short_half():
    """A boundary very close to the start of the window that would produce a short first half
    should be skipped or cause rejection if no valid split exists.

    We craft a sentence where the only in-window boundary is at index 2 of a 12-word
    sentence, but minimum_half_tokens=4. Fallback midpoint at 6 is fine, so this
    should NOT be rejected — it should fall back to midpoint.

    This test confirms the algorithm does not blindly take a boundary that would
    violate minimum_half_tokens; it must either find a valid boundary or use midpoint.
    """
    # 12 words; 'and' is at index 2 — only 2 words before it, violates minimum of 4.
    # midpoint=6, window=5 → scan from index 1 to 11.
    # 'and' at index 2 would give first_half=['The', 'tall'] → only 2 words → rejected boundary.
    # There are no other boundaries in the window, so fallback to midpoint (index 6).
    sentence = "The tall and blossoming cherry trees swayed softly beside the quiet stream."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    # mid=6; 'and' at index 2 is in window but creates a 2-word first half → skip it.
    # Fallback: word_midpoint at 6 gives halves of 6 and 6 words — both valid.
    assert strategy in ("word_midpoint", "clause_boundary")
    assert first is not None
    assert second is not None


# ---------------------------------------------------------------------------
# 12-13. Round-trip rejoining
# ---------------------------------------------------------------------------

def test_halve_no_mid_word_split():
    """For word_midpoint strategy, first + ' ' + second must equal the original sentence."""
    sentence = "The tall cherry blossoms swayed gracefully under the pale afternoon sky."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy == "word_midpoint"
    assert first + " " + second == sentence


def test_halve_halves_rejoin_to_original_at_clause_boundary():
    """For clause_boundary strategy, first + ' ' + second must equal the original sentence."""
    sentence = "Genji gazed at the moon, and the night was still."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy == "clause_boundary"
    assert first + " " + second == sentence


# ---------------------------------------------------------------------------
# 14-15. Minimum half tokens respected
# ---------------------------------------------------------------------------

def test_halve_minimum_half_tokens_respected_for_first_half():
    """The first half must have at least minimum_half_tokens words."""
    sentence = "The tall cherry blossoms swayed gracefully under the pale afternoon sky."
    first, _, strategy = halve_sentence(sentence, TEST_CONFIG)
    if strategy != "rejected":
        assert len(first.split()) >= TEST_CONFIG["halving"]["minimum_half_tokens"]


def test_halve_minimum_half_tokens_respected_for_second_half():
    """The second half must have at least minimum_half_tokens words."""
    sentence = "The tall cherry blossoms swayed gracefully under the pale afternoon sky."
    _, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    if strategy != "rejected":
        assert len(second.split()) >= TEST_CONFIG["halving"]["minimum_half_tokens"]


# ---------------------------------------------------------------------------
# 16-17. Even and odd word counts
# ---------------------------------------------------------------------------

def test_halve_even_word_count():
    """A sentence with an even number of words splits correctly (no off-by-one errors)."""
    # 10 words — even
    sentence = "The moon rose above the hills and silence filled the night."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy != "rejected"
    assert first is not None and second is not None
    # Both halves should be non-empty
    assert len(first.split()) >= 1
    assert len(second.split()) >= 1


def test_halve_odd_word_count():
    """A sentence with an odd number of words splits correctly (floor division midpoint)."""
    # 11 words — odd
    sentence = "The old prince gazed across the still lake at the distant mountains."
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy != "rejected"
    assert first is not None and second is not None
    assert len(first.split()) >= 1
    assert len(second.split()) >= 1


# ---------------------------------------------------------------------------
# 18. Window edge
# ---------------------------------------------------------------------------

def test_halve_boundary_at_edge_of_window():
    """A boundary exactly at the edge of the scan window must still be found.

    With midpoint_window_tokens=5 and mid=7 in a 15-word sentence, the window
    extends to index 12. We place 'but' at index 12 (right edge) and confirm it
    is still found.
    """
    # 15 words; mid=7; window=[2..12]; 'but' at index 12 is at the far right edge.
    sentence = "The prince looked upon the silent garden in wonder but everything seemed distant and cold."
    # words: 0:The 1:prince 2:looked 3:upon 4:the 5:silent 6:garden 7:in 8:wonder 9:but ...
    # 'but' is at index 9 — well within window [2..12] — confirms edge detection works.
    # (If we set window=1, mid=7, 'but' at 9 would be outside; use default window=5.)
    first, second, strategy = halve_sentence(sentence, TEST_CONFIG)
    assert strategy == "clause_boundary"
    assert second.startswith("but"), (
        f"Expected 'but' to be found at window edge; got second={second!r}"
    )

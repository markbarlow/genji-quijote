"""Unit tests for pipeline/sentence_splitter.py.

Uses a lightweight mock nlp object that splits on double newlines.
"""

import pytest

from pipeline.sentence_splitter import split_sentences


# ---------------------------------------------------------------------------
# Mock spaCy objects for testing (no heavy model loading)
# ---------------------------------------------------------------------------


class MockSent:
    """Represents a sentence object with a text attribute."""

    def __init__(self, text):
        self.text = text


class MockDoc:
    """Minimal spaCy-like Doc object with sentence segmentation."""

    def __init__(self, text):
        # Split on double newlines to simulate sentence boundaries
        self._sents = [MockSent(s.strip()) for s in text.split("\n\n") if s.strip()]

    @property
    def sents(self):
        return iter(self._sents)


class MockNlp:
    """Minimal spaCy-like nlp that returns MockDoc."""

    def __call__(self, text):
        return MockDoc(text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_split_sentences_returns_list_of_strings():
    """Verify split_sentences returns a list of strings."""
    mock_nlp = MockNlp()
    text = "First sentence.\n\nSecond sentence."
    result = split_sentences(text, mock_nlp)
    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)


def test_split_sentences_strips_whitespace():
    """Verify no leading/trailing whitespace in any returned sentence."""
    mock_nlp = MockNlp()
    text = "  First sentence.  \n\n  Second sentence.  "
    result = split_sentences(text, mock_nlp)
    for sentence in result:
        assert sentence == sentence.strip(), f"Sentence has whitespace: {repr(sentence)}"


def test_split_sentences_excludes_empty_strings():
    """Verify empty strings are filtered out."""
    mock_nlp = MockNlp()
    text = "First sentence.\n\n\n\nSecond sentence."
    result = split_sentences(text, mock_nlp)
    assert "" not in result
    assert all(len(s) > 0 for s in result)


def test_split_sentences_passes_text_to_nlp():
    """Verify sentences from the mock nlp appear in the output."""
    mock_nlp = MockNlp()
    text = "First sentence.\n\nSecond sentence.\n\nThird sentence."
    result = split_sentences(text, mock_nlp)
    assert len(result) == 3
    assert "First sentence." in result
    assert "Second sentence." in result
    assert "Third sentence." in result

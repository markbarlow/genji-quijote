"""Smoke tests for text_loader module."""

from pipeline.text_loader import load_text


def test_load_text_returns_non_empty_string():
    """Verify load_text returns a non-empty string."""
    path = "/Users/Mark/Github/genji-quijote/source-materials/gutenberg-source-text/don-quijote-volume-1-volume-2.txt"
    result = load_text(path)
    assert isinstance(result, str)
    assert len(result) > 0


def test_load_text_removes_utf8_bom():
    """Verify load_text strips the UTF-8 BOM character if present."""
    path = "/Users/Mark/Github/genji-quijote/source-materials/gutenberg-source-text/don-quijote-volume-1-volume-2.txt"
    result = load_text(path)
    assert not result.startswith("\ufeff"), "Result should not start with UTF-8 BOM"


def test_load_text_normalizes_crlf_to_lf():
    """Verify load_text converts CRLF line endings to LF (no \\r characters)."""
    path = "/Users/Mark/Github/genji-quijote/source-materials/gutenberg-source-text/don-quijote-volume-1-volume-2.txt"
    result = load_text(path)
    assert "\r" not in result, "Result should not contain carriage return characters"


def test_load_text_contains_expected_content():
    """Verify load_text preserves expected text content."""
    path = "/Users/Mark/Github/genji-quijote/source-materials/gutenberg-source-text/don-quijote-volume-1-volume-2.txt"
    result = load_text(path)
    assert "Don Quixote" in result, "Result should contain 'Don Quixote'"

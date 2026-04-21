"""Unit tests for text_loader module using pytest fixtures."""

import pytest
from pipeline.text_loader import load_text


def test_load_text_returns_non_empty_string(tmp_path):
    """Verify load_text returns a non-empty string."""
    p = tmp_path / "test.txt"
    p.write_text("Hello World", encoding="utf-8")
    result = load_text(p)
    assert isinstance(result, str)
    assert len(result) > 0


def test_load_text_removes_utf8_bom(tmp_path):
    """Verify load_text strips the UTF-8 BOM character if present."""
    p = tmp_path / "test.txt"
    p.write_bytes(b"\xef\xbb\xbfHello World")
    result = load_text(p)
    assert not result.startswith("\ufeff"), "Result should not start with UTF-8 BOM"
    assert result == "Hello World"


def test_load_text_without_bom(tmp_path):
    """Verify load_text works correctly with files that have no BOM."""
    p = tmp_path / "test.txt"
    p.write_text("Hello World", encoding="utf-8")
    result = load_text(p)
    assert result == "Hello World"
    assert not result.startswith("\ufeff")


def test_load_text_normalizes_crlf_to_lf(tmp_path):
    """Verify load_text converts CRLF line endings to LF (no \\r characters)."""
    p = tmp_path / "test.txt"
    p.write_bytes(b"Hello\r\nWorld\r\n")
    result = load_text(p)
    assert "\r" not in result, "Result should not contain carriage return characters"
    assert result == "Hello\nWorld\n"


def test_load_text_lf_only_unchanged(tmp_path):
    """Verify load_text preserves LF-only line endings correctly."""
    p = tmp_path / "test.txt"
    p.write_bytes(b"Hello\nWorld\n")
    result = load_text(p)
    assert result == "Hello\nWorld\n"
    assert "\r" not in result


def test_load_text_mixed_line_endings(tmp_path):
    """Verify load_text removes all \\r in files with mixed CRLF and LF."""
    p = tmp_path / "test.txt"
    p.write_bytes(b"Line1\r\nLine2\nLine3\r\n")
    result = load_text(p)
    assert "\r" not in result
    assert result == "Line1\nLine2\nLine3\n"


def test_load_text_empty_file(tmp_path):
    """Verify load_text returns empty string for empty files without error."""
    p = tmp_path / "test.txt"
    p.write_text("", encoding="utf-8")
    result = load_text(p)
    assert result == ""


def test_load_text_nonexistent_file():
    """Verify load_text raises FileNotFoundError for nonexistent paths."""
    nonexistent = "/tmp/this_file_does_not_exist_12345.txt"
    with pytest.raises(FileNotFoundError):
        load_text(nonexistent)

"""Unit tests for pipeline/text_cleaner.py.

Uses short hand-crafted fixture strings that mimic the real Gutenberg source
format — no real source files are read here.
"""

import pytest

from pipeline.text_cleaner import (
    remove_footnote_definitions,
    strip_genji_footnote_markers,
    strip_gutenberg_wrapper,
    tag_chapter_headings,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GENJI_RAW = """\
The Project Gutenberg eBook of The Tale of Genji

*** START OF THE PROJECT GUTENBERG EBOOK THE TALE OF GENJI ***

CHAPTER I
KIRITSUBO[1]

In the reign of a certain Emperor[2], whose name we do not know, there was, among the many ladies of the Court, one who was favoured far beyond all the rest.

[1] This chapter title means "Paulownia Pavilion."
[2] The Emperor referred to here is fictional.

CHAPTER II
THE BROOM-TREE[3]

At the court of the same Emperor, in the seventh year of his reign.

[3] Broom-tree is a poetic symbol.

*** END OF THE PROJECT GUTENBERG EBOOK THE TALE OF GENJI ***
"""

QUIXOTE_RAW = """\
The Project Gutenberg eBook of Don Quixote

*** START OF THE PROJECT GUTENBERG EBOOK DON QUIXOTE ***

CHAPTER I.
WHICH TREATS OF THE CHARACTER AND PURSUITS OF THE FAMOUS
GENTLEMAN DON QUIXOTE OF LA MANCHA

In a village of La Mancha, the name of which I have no desire to call to mind, there lived not long since one of those gentlemen that keep a lance in the lance-rack.

CHAPTER II.
OF THE FIRST SALLY THE INGENIOUS DON QUIXOTE MADE
FROM HIS NATIVE VILLAGE

The first sally our new-made knight made from his village was such a one as almost caused him to abandon the career he had so lately entered upon.

*** END OF THE PROJECT GUTENBERG EBOOK DON QUIXOTE ***
"""

# ---------------------------------------------------------------------------
# strip_gutenberg_wrapper tests
# ---------------------------------------------------------------------------


def test_strip_gutenberg_wrapper_removes_header():
    """Header boilerplate (before START marker) must not appear in the result."""
    result = strip_gutenberg_wrapper(GENJI_RAW)
    assert "Project Gutenberg eBook" not in result


def test_strip_gutenberg_wrapper_removes_footer():
    """Footer marker line must not appear in the result."""
    result = strip_gutenberg_wrapper(GENJI_RAW)
    assert "END OF THE PROJECT GUTENBERG EBOOK" not in result


def test_strip_gutenberg_wrapper_preserves_body():
    """Literary body text must be present after stripping."""
    result = strip_gutenberg_wrapper(GENJI_RAW)
    assert "In the reign" in result


# ---------------------------------------------------------------------------
# strip_genji_footnote_markers tests
# ---------------------------------------------------------------------------


def test_strip_genji_footnote_markers_removes_inline_markers():
    """Inline markers like [1] and [2] must be absent after stripping."""
    sample = "In the reign of a certain Emperor[2], whose name we do not know."
    result = strip_genji_footnote_markers(sample)
    assert "[1]" not in result
    assert "[2]" not in result


def test_strip_genji_footnote_markers_preserves_text():
    """Words surrounding the marker must remain intact."""
    sample = "Yang Kuei-fei.[2] She was the daughter of a great lord."
    result = strip_genji_footnote_markers(sample)
    assert "Yang Kuei-fei." in result
    assert "She was the daughter" in result


# ---------------------------------------------------------------------------
# remove_footnote_definitions tests
# ---------------------------------------------------------------------------


def test_remove_footnote_definitions_removes_definition_lines():
    """Lines starting with [N] (footnote definitions) must be removed."""
    sample = (
        "Some body text here.\n"
        "[1] This chapter title means something.\n"
        "[2] Another note.\n"
        "More body text.\n"
    )
    result = remove_footnote_definitions(sample)
    assert "[1] This chapter title" not in result
    assert "[2] Another note" not in result


def test_remove_footnote_definitions_preserves_body_text():
    """Body sentences must survive footnote definition removal."""
    sample = (
        "Some body text here.\n"
        "[1] This chapter title means something.\n"
        "More body text.\n"
    )
    result = remove_footnote_definitions(sample)
    assert "Some body text here." in result
    assert "More body text." in result


# ---------------------------------------------------------------------------
# tag_chapter_headings tests — Genji
# ---------------------------------------------------------------------------


def test_tag_chapter_headings_genji_returns_correct_count():
    """Two chapters in the genji fixture must produce exactly two tuples."""
    body = strip_gutenberg_wrapper(GENJI_RAW)
    chapters = tag_chapter_headings(body, source="genji")
    assert len(chapters) == 2


def test_tag_chapter_headings_genji_labels():
    """Chapter labels must be 'CHAPTER I' and 'CHAPTER II' (no period)."""
    body = strip_gutenberg_wrapper(GENJI_RAW)
    chapters = tag_chapter_headings(body, source="genji")
    labels = [label for label, _ in chapters]
    assert "CHAPTER I" in labels
    assert "CHAPTER II" in labels


def test_tag_chapter_headings_genji_body_excludes_heading():
    """The heading line itself ('CHAPTER I') must not appear in the body text."""
    body = strip_gutenberg_wrapper(GENJI_RAW)
    chapters = tag_chapter_headings(body, source="genji")
    for _, chapter_body in chapters:
        assert "CHAPTER I" not in chapter_body
        assert "CHAPTER II" not in chapter_body


# ---------------------------------------------------------------------------
# tag_chapter_headings tests — Quixote
# ---------------------------------------------------------------------------


def test_tag_chapter_headings_quijote_returns_correct_count():
    """Two chapters in the quixote fixture must produce exactly two tuples."""
    body = strip_gutenberg_wrapper(QUIXOTE_RAW)
    chapters = tag_chapter_headings(body, source="quijote")
    assert len(chapters) == 2


def test_tag_chapter_headings_quijote_body_excludes_subtitle():
    """ALL-CAPS subtitle lines must not appear in any chapter body."""
    body = strip_gutenberg_wrapper(QUIXOTE_RAW)
    chapters = tag_chapter_headings(body, source="quijote")
    for _, chapter_body in chapters:
        # These subtitle fragments are ALL-CAPS and must be excluded
        assert "WHICH TREATS OF THE CHARACTER" not in chapter_body
        assert "OF THE FIRST SALLY" not in chapter_body

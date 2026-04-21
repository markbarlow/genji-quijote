"""text_cleaner.py — clean raw Gutenberg texts for the genji-quijote pipeline.

All functions are pure (no file I/O). They receive strings and return strings
or lists of tuples.  The expected input has already been BOM-stripped and
CRLF-normalised by text_loader.py.
"""

import re


def strip_gutenberg_wrapper(text: str) -> str:
    """Remove the Project Gutenberg header and footer, returning only the body.

    The header ends on the line containing
    '*** START OF THE PROJECT GUTENBERG EBOOK'.
    The footer begins on the line containing
    '*** END OF THE PROJECT GUTENBERG EBOOK'.
    Everything between those two sentinel lines (exclusive) is returned.

    Parameters
    ----------
    text : str
        Raw text string from a Project Gutenberg file, with CRLF already
        normalised to LF.

    Returns
    -------
    str
        The literary body text with header and footer boilerplate removed.
    """
    lines = text.splitlines()

    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if "*** START OF THE PROJECT GUTENBERG EBOOK" in line:
            start_idx = i  # body begins on the line *after* this
        elif "*** END OF THE PROJECT GUTENBERG EBOOK" in line:
            end_idx = i    # body ends on the line *before* this
            break

    if start_idx is None or end_idx is None:
        # Sentinel lines not found — return the whole text unchanged rather
        # than silently dropping content.
        return text

    body_lines = lines[start_idx + 1 : end_idx]
    return "\n".join(body_lines)


def strip_genji_footnote_markers(text: str) -> str:
    """Strip inline footnote reference markers (e.g. [1], [23]) from text.

    Only the bare bracketed-number markers that appear inline mid-sentence are
    removed.  Footnote *definition* lines (lines that *start* with [N]) are
    left untouched — use remove_footnote_definitions() for those.

    Parameters
    ----------
    text : str
        Cleaned or partially-cleaned Genji body text.

    Returns
    -------
    str
        Text with all occurrences of ``[<digits>]`` removed.
    """
    # \[\d+\] matches a literal '[', one-or-more digits, then ']'
    return re.sub(r"\[\d+\]", "", text)


def remove_footnote_definitions(text: str) -> str:
    """Remove footnote definition lines from the text.

    A footnote definition line is a line whose first non-whitespace content
    matches ``[N]`` followed by a space and further text — e.g.
    ``[1] This chapter title means "Paulownia Pavilion."``.

    Only whole lines are removed; inline markers elsewhere in the text are
    not affected (use strip_genji_footnote_markers() for those).

    Parameters
    ----------
    text : str
        Body text that may contain footnote definition lines.

    Returns
    -------
    str
        Text with footnote definition lines removed.
    """
    # re.MULTILINE makes ^ match at the start of each line, not just the
    # start of the string.  The pattern requires at least one character after
    # the closing bracket so we don't accidentally strip inline-only markers
    # on their own line (edge case, but keeps the function conservative).
    return re.sub(r"^\[\d+\].+$", "", text, flags=re.MULTILINE)


def tag_chapter_headings(text: str, source: str) -> list[tuple[str, str]]:
    """Split text into chapters, returning (chapter_label, chapter_body) pairs.

    The heading line itself is used as the chapter label and is excluded from
    the body.  Additional non-body lines that immediately follow the heading
    are also excluded:

    * **Genji**: the chapter title line (e.g. ``KIRITSUBO[1]``) that follows
      each ``CHAPTER N`` heading is excluded from the body.
    * **Quixote**: one or more ALL-CAPS subtitle lines (``line.isupper()`` and
      ``len(line.strip()) > 3``) that immediately follow the ``CHAPTER N.``
      heading are excluded from the body.

    Parameters
    ----------
    text : str
        Literary body text (Gutenberg wrapper already removed).
    source : str
        Either ``'genji'`` or ``'quijote'``.  Controls the heading regex and
        the subtitle-exclusion logic.

    Returns
    -------
    list[tuple[str, str]]
        A list of ``(chapter_label, chapter_body)`` tuples in document order.
        The chapter_label is the raw heading string (e.g. ``'CHAPTER I'``).
        The chapter_body is the text between headings with heading/subtitle
        lines stripped, stripped of leading/trailing blank lines.

    Raises
    ------
    ValueError
        If *source* is not ``'genji'`` or ``'quijote'``.
    """
    if source == "genji":
        # Genji headings: 'CHAPTER' + space + Roman numerals, NO trailing period
        heading_re = re.compile(r"^(CHAPTER [IVXLC]+)$", re.MULTILINE)
    elif source == "quijote":
        # Quixote headings: 'CHAPTER' + space + Roman numerals + period
        heading_re = re.compile(r"^(CHAPTER [IVXLC]+\.)$", re.MULTILINE)
    else:
        raise ValueError(f"source must be 'genji' or 'quijote', got {source!r}")

    lines = text.splitlines()
    chapters: list[tuple[str, str]] = []

    # Collect the line indices of every heading line
    heading_indices: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = heading_re.match(line.strip())
        if m:
            heading_indices.append((i, m.group(1)))

    for pos, (heading_line_idx, label) in enumerate(heading_indices):
        # The body of this chapter runs from the line after the heading up to
        # (but not including) the next heading, or to the end of the text.
        if pos + 1 < len(heading_indices):
            next_heading_idx = heading_indices[pos + 1][0]
            body_lines = lines[heading_line_idx + 1 : next_heading_idx]
        else:
            body_lines = lines[heading_line_idx + 1 :]

        # Strip the immediately-following non-body lines
        body_lines = _strip_non_body_prefix(body_lines, source)

        chapter_body = "\n".join(body_lines).strip()
        chapters.append((label, chapter_body))

    return chapters


def _strip_non_body_prefix(lines: list[str], source: str) -> list[str]:
    """Remove the non-body lines that immediately follow a chapter heading.

    For Genji, skip exactly one chapter-title line (typically a short line
    that may contain ``[N]`` markers).
    For Quixote, skip all leading ALL-CAPS subtitle lines.

    Parameters
    ----------
    lines : list[str]
        Lines of the chapter body, starting immediately after the heading.
    source : str
        ``'genji'`` or ``'quijote'``.

    Returns
    -------
    list[str]
        Lines with the non-body prefix removed.
    """
    if not lines:
        return lines

    if source == "genji":
        # Skip blank lines, then skip exactly one title line (non-blank).
        i = 0
        # Advance past any leading blank lines
        while i < len(lines) and not lines[i].strip():
            i += 1
        # Skip the single title line that follows the heading
        if i < len(lines):
            i += 1
        return lines[i:]

    # source == 'quijote'
    # Skip blank lines, then skip consecutive ALL-CAPS subtitle lines.
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1

    # A subtitle line: stripped text is all-uppercase and longer than 3 chars
    # (guards against short tokens like "I" or "II" that are trivially upper)
    while i < len(lines) and lines[i].strip() and lines[i].strip().isupper() and len(lines[i].strip()) > 3:
        i += 1

    return lines[i:]

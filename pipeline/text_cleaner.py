"""text_cleaner.py — clean raw Gutenberg texts for the genji-quijote pipeline.

All functions are pure (no file I/O). They receive strings and return strings
or lists of tuples.  The expected input has already been BOM-stripped and
CRLF-normalised by text_loader.py.
"""

import re


def strip_gutenberg_wrapper(text: str) -> str:
    """Remove the Project Gutenberg header and footer, returning only the body.

    Two header formats are handled:

    * **Sentinel format**: the header ends on the line containing
      ``'*** START OF THE PROJECT GUTENBERG EBOOK'`` and the footer begins on
      the line containing ``'*** END OF THE PROJECT GUTENBERG EBOOK'``.
      Everything between those two lines (exclusive) is returned.

    * **Dash-separator format**: some files have 4 metadata lines (Title /
      Author / Translator / Release Date) followed by a bare ``---`` line
      instead of the ``***`` sentinels.  In this case everything up to and
      including the first ``---`` line is stripped, and the rest of the file
      is returned as-is (no footer stripping is needed because these files
      have no footer boilerplate).

    If neither format is detected the text is returned unchanged rather than
    silently dropping content.

    Parameters
    ----------
    text : str
        Raw text string from a Project Gutenberg file, with CRLF already
        normalised to LF and the BOM already removed.

    Returns
    -------
    str
        The literary body text with header (and footer) boilerplate removed.
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

    if start_idx is not None and end_idx is not None:
        body_lines = lines[start_idx + 1 : end_idx]
        return "\n".join(body_lines)

    # Fall back to dash-separator format: strip everything up to and including
    # the first bare '---' line (the short metadata block at the top of these
    # files uses '---' as its terminator rather than the *** sentinels).
    for i, line in enumerate(lines):
        if line.strip() == "---":
            body_lines = lines[i + 1 :]
            return "\n".join(body_lines)

    # Neither format matched — return unchanged.
    return text


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
    # Anchored bracket syntax prevents matching things like "[chapter]"; only
    # pure digit sequences (footnote indices) are removed.
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
    # \s* allows for optional leading whitespace — Genji definitions start at
    # column 0, but this keeps the pattern robust for other inputs.
    return re.sub(r"^\s*\[\d+\].+$", "", text, flags=re.MULTILINE)


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

    # For sources where the same Roman-numeral label can appear more than once
    # (e.g. Quijote Volume 1 and Volume 2 both start at CHAPTER I.), we need
    # unique labels.  Detect duplicates and retrofit volume prefixes so that
    # downstream code can always use the label as a unique key.
    raw_labels = [label for _, label in heading_indices]
    label_counts: dict[str, int] = {}
    for lbl in raw_labels:
        label_counts[lbl] = label_counts.get(lbl, 0) + 1

    has_duplicates = any(count > 1 for count in label_counts.values())

    if has_duplicates:
        # Assign volume numbers: a new volume begins whenever a heading label
        # is seen that was already used in the *current* volume.  We track the
        # set of labels used so far in the current volume and reset it at each
        # volume boundary.
        volume = 1
        current_volume_seen: set[str] = set()
        unique_labels: list[str] = []
        for lbl in raw_labels:
            if lbl in current_volume_seen:
                # This label has already appeared in the current volume —
                # a new volume is starting.
                volume += 1
                current_volume_seen = set()
            current_volume_seen.add(lbl)
            unique_labels.append(f"V{volume} {lbl}")
        heading_indices = [(idx, unique_labels[i]) for i, (idx, _) in enumerate(heading_indices)]

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
    # (guards against short tokens like "I" or "II" that are trivially upper).
    # A blank line acts as a sentinel — once we hit one, the subtitle block is
    # over even if more uppercase lines appear later in the body.
    while (
        i < len(lines)
        and lines[i].strip()  # blank line ends the subtitle block
        and lines[i].strip().isupper()
        and len(lines[i].strip()) > 3
    ):
        i += 1

    return lines[i:]

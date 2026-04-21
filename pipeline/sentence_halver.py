"""sentence_halver.py — split a sentence into two halves at a natural clause boundary.

Implements the core splitting algorithm for the Genji–Quixote mashup pipeline.
The algorithm respects word boundaries at all times (tokenises by whitespace,
reassembles with spaces) and never inserts separator characters between the
output halves — the caller joins them directly in the display field.

Usage:
    from pipeline.sentence_halver import halve_sentence
    first, second, strategy = halve_sentence(sentence, config)
"""


def halve_sentence(sentence: str, config: dict) -> tuple[str, str, str] | tuple[None, None, str]:
    """Split a sentence into two halves at a natural clause boundary near the midpoint.

    Tokenises by whitespace (word boundaries always respected — splits occur between
    words, never mid-word). Scans a window of tokens around the midpoint for a
    clause boundary character or conjunction. Splits there if found; falls back to
    the word midpoint.

    Parameters
    ----------
    sentence : str
        The sentence to halve. Should be a cleaned sentence string.
    config : dict
        Configuration dict with a "halving" section. Expected keys:
            midpoint_window_tokens : int  — how many tokens either side of midpoint to scan
            minimum_half_tokens : int     — minimum word count for each half
            boundary_priority : list[str] — clause boundary markers in priority order;
                                            single characters are treated as punctuation
                                            (matched against the last char of the previous
                                            word), multi-character strings are conjunctions
                                            (matched against the word itself)

    Returns
    -------
    tuple[str, str, str]
        (first_half, second_half, strategy) where strategy is one of:
        "clause_boundary" — split at a clause boundary character/conjunction
        "word_midpoint"   — fell back to splitting at word midpoint
    tuple[None, None, str]
        (None, None, "rejected") when either half would be shorter than minimum_half_tokens.
    """
    cfg = config["halving"]
    window: int = cfg["midpoint_window_tokens"]
    minimum: int = cfg["minimum_half_tokens"]
    boundary_priority: list[str] = cfg["boundary_priority"]

    # Step 1 — Tokenise by whitespace. All subsequent logic operates on whole
    # tokens, guaranteeing we never split mid-word.
    words: list[str] = sentence.split()
    n: int = len(words)

    # Step 2 — Early rejection: if the sentence doesn't have enough words to
    # form two halves each meeting the minimum, there is no valid split at all.
    if n < 2 * minimum:
        return (None, None, "rejected")

    # Step 3 — Midpoint index (floor division, so the first half is never longer
    # than the second for odd-length sentences).
    mid: int = n // 2

    # Step 4 — Clamp the scan window to valid index range.
    # We scan from index 1 (there must be at least one word in the first half)
    # to n-1 (there must be at least one word in the second half). Splitting
    # BEFORE index i means first_half = words[:i], second_half = words[i:].
    window_start: int = max(1, mid - window)
    window_end: int = min(n - 1, mid + window)

    # Step 5 — Build a candidate list ordered by closeness to the midpoint.
    # We alternate left and right from mid so that the CLOSEST candidate is
    # checked first. This implements "closest to midpoint wins" without needing
    # a sort pass.
    candidates: list[int] = _indices_by_closeness(mid, window_start, window_end)

    # Step 5 (cont.) — Walk the candidates in closeness order. For each split
    # point i we check two conditions:
    #   a) words[i] is itself a boundary conjunction (e.g. "but", "and")
    #   b) words[i-1] ends with a boundary punctuation character (e.g. ',', ';')
    # Both checks use the boundary_priority list, which places punctuation chars
    # before conjunctions. Single-character entries are punctuation; longer
    # entries are conjunctions. We check the priority list in order so that if
    # two markers tie on distance, higher-priority marker wins.
    split_index: int | None = None
    for i in candidates:
        # Build a priority-ordered check for this candidate position.
        for marker in boundary_priority:
            if len(marker) == 1:
                # Punctuation check: does the word just BEFORE the split end with this char?
                # We require i > 0 so words[i-1] is valid (always true given window_start >= 1).
                if words[i - 1][-1] == marker:
                    split_index = i
                    break
            else:
                # Conjunction check: is the word AT the split point this conjunction?
                if words[i] == marker:
                    split_index = i
                    break
        if split_index is not None:
            break

    # Step 6 — If no boundary was found in the window, fall back to the word
    # midpoint. This is the "safe" split — it guarantees each half has at least
    # floor(n/2) words, which the step-2 guard already confirmed is >= minimum.
    strategy: str
    if split_index is not None:
        strategy = "clause_boundary"
    else:
        split_index = mid
        strategy = "word_midpoint"

    # Step 7 — Enforce minimum half lengths. A clause-boundary split could place
    # the boundary very close to one end of the sentence (e.g. a comma in the
    # third word). If either resulting half is too short, reject the split and
    # fall back to midpoint. If even the midpoint produces a short half (which
    # the step-2 guard prevents), return rejected.
    first_words: list[str] = words[:split_index]
    second_words: list[str] = words[split_index:]

    if len(first_words) < minimum or len(second_words) < minimum:
        if strategy == "clause_boundary":
            # The clause boundary created an invalid split — fall back to midpoint.
            split_index = mid
            first_words = words[:split_index]
            second_words = words[split_index:]
            strategy = "word_midpoint"
            # Check again after fallback (step-2 guard makes this pass, but be explicit).
            if len(first_words) < minimum or len(second_words) < minimum:
                return (None, None, "rejected")
        else:
            # Midpoint split itself violated minimum — sentence is too short.
            return (None, None, "rejected")

    # Step 8 — Reassemble with spaces. The caller joins first_half + " " + second_half
    # directly (no extra separator), so the round-trip reproduces the original sentence.
    first_half: str = " ".join(first_words)
    second_half: str = " ".join(second_words)

    # Step 9 — Return the two halves and the split strategy.
    return (first_half, second_half, strategy)


def _indices_by_closeness(mid: int, start: int, end: int) -> list[int]:
    """Return indices in [start, end] ordered by closeness to mid, ties broken left-first.

    We scan outward from mid in alternating left/right steps so that closer
    indices appear first. This ordering means the first valid boundary we
    encounter in the main loop is automatically the closest to the midpoint —
    no sorting or distance comparison needed later.

    Parameters
    ----------
    mid : int
        The midpoint index (centre of the scan window).
    start : int
        Inclusive lower bound of the window.
    end : int
        Inclusive upper bound of the window.

    Returns
    -------
    list[int]
        Indices in [start, end] sorted by |index - mid| ascending, ties broken
        by preferring the lower index (left-biased on equidistant pairs).
    """
    # Collect all indices in the window then sort by distance from mid.
    # Left-bias on ties: Python's sort is stable; generating left-to-right first
    # and sorting by abs distance preserves left-over-right for equal distances.
    indices = list(range(start, end + 1))
    indices.sort(key=lambda i: abs(i - mid))
    return indices

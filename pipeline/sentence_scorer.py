"""Sentence scoring module for literary text interestingness.

Assigns a raw floating-point score to a cleaned sentence based on four
weighted components: length (sweet-spot), character presence, place-name
heuristic, and lexical diversity (type-token ratio). The score is NOT
normalised here; normalisation to [0, 1] across the candidate pool
happens later in pair_generator.
"""

import re


# ---------------------------------------------------------------------------
# Stopword set for lexical diversity filtering
# ---------------------------------------------------------------------------

_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
    'his', 'her', 'their', 'its', 'he', 'she', 'they', 'it', 'i', 'not',
    'that', 'this', 'which', 'who', 'had', 'have', 'has', 'would', 'could',
    'did', 'do', 'said', 'as', 'up', 'so', 'if', 'my', 'your',
}

# Regex to find a capitalised word that is NOT the first word in the sentence.
# Negative lookbehind (?<!\. ) prevents matching the start of a new sentence
# fragment after a full stop, though in practice sentences are already split.
# We use \b word boundaries for whole-word matching.
_INTERNAL_CAPITAL_RE = re.compile(r'(?<!\. )\b[A-Z][a-z]+\b')


def _length_score(sentence: str, weights: dict) -> float:
    """Compute a 0.0–1.0 length score for the sentence.

    Returns 1.0 when word count is within [length_sweet_spot_min,
    length_sweet_spot_max]. Falls off linearly to 0.0 for counts below min
    or above max, reaching 0.0 at word-count 0 (below) or at
    2 * max - min (above). The fall-off is linear proportional to how far
    outside the range the count sits.

    Parameters
    ----------
    sentence : str
        The sentence to measure.
    weights : dict
        The "sentence" section of scoring_weights.json.

    Returns
    -------
    float
        A value in [0.0, 1.0].
    """
    word_count = len(sentence.split())
    lo = weights["length_sweet_spot_min"]
    hi = weights["length_sweet_spot_max"]

    if lo <= word_count <= hi:
        # Perfect range → full score
        return 1.0

    if word_count < lo:
        # Below minimum: linear fall-off from lo → 0 down to word-count 0
        # At lo: 1.0. At 0: 0.0.
        return word_count / lo if lo > 0 else 0.0

    # Above maximum: linear fall-off from hi → 0 upward.
    # Treat the range above hi as symmetric to the range below lo.
    # At hi: 1.0. At hi + lo: 0.0 (distance lo above the top).
    distance_above = word_count - hi
    return max(0.0, 1.0 - distance_above / lo) if lo > 0 else 0.0


def _character_score(detected_chars: list, registry: dict, weights: dict) -> float:
    """Compute a character-presence component.

    For each detected character, looks up its rank and score_weight from the
    registry. Major characters use `character_major_score` as the weight
    multiplier; minor characters use `character_minor_score`. The sum of
    score_weights per rank group is capped at 1.0 before multiplying by the
    rank weight — this prevents a sentence crammed with minor characters from
    outscoring one with a single major character.

    Parameters
    ----------
    detected_chars : list[str]
        Canonical character names found in the sentence.
    registry : dict
        Source-specific subtree of character_ranks.json.
    weights : dict
        The "sentence" section of scoring_weights.json.

    Returns
    -------
    float
        Combined character component value.
    """
    major_total = 0.0
    minor_total = 0.0

    for char_key in detected_chars:
        char_data = registry.get(char_key)
        if char_data is None:
            # Character was detected but is not in this registry subtree; skip.
            continue
        sw = char_data.get("score_weight", 0.0)
        rank = char_data.get("rank", "minor")

        if rank == "major":
            major_total += sw
        else:
            minor_total += sw

    # Cap each group at 1.0 before weighting, so the multiplier is applied to
    # a normalised [0, 1] value rather than an unbounded sum.
    capped_major = min(1.0, major_total)
    capped_minor = min(1.0, minor_total)

    return (
        capped_major * weights["character_major_score"]
        + capped_minor * weights["character_minor_score"]
    )


def _place_name_score(sentence: str, weights: dict) -> float:
    """Detect internal capitalised words as a proxy for place names.

    Heuristic: any capitalised word (\b[A-Z][a-z]+\b) that is NOT the
    very first word of the sentence is treated as a potential place name
    or proper noun. Binary: 1.0 if found, 0.0 otherwise.

    The first word is excluded because any sentence starts with a capital,
    which carries no toponym signal.

    Parameters
    ----------
    sentence : str
        The sentence to check.
    weights : dict
        The "sentence" section of scoring_weights.json.

    Returns
    -------
    float
        `place_name_bonus` if an internal capital is detected, else 0.0.
    """
    # Split to find where the first word ends so we can skip it.
    first_space = sentence.find(' ')
    if first_space == -1:
        # Single-word sentence: nothing to search after first word.
        return 0.0

    # Search only the portion after the first word.
    remainder = sentence[first_space + 1:]
    if _INTERNAL_CAPITAL_RE.search(remainder):
        return weights["place_name_bonus"]

    return 0.0


def _lexical_diversity_score(sentence: str, weights: dict) -> float:
    """Compute a type-token ratio (TTR) over non-stopword content words.

    Content words are all lowercase tokens that are not in _STOPWORDS.
    TTR = unique content words / total content words. Returns 0.0 if there
    are no content words (e.g. an all-stopword sentence).

    Parameters
    ----------
    sentence : str
        The sentence to analyse.
    weights : dict
        The "sentence" section of scoring_weights.json.

    Returns
    -------
    float
        TTR × lexical_diversity_weight.
    """
    # Tokenise by splitting on whitespace, lowercase, strip punctuation edges.
    tokens = [w.strip(".,;:!?\"'()[]—-").lower() for w in sentence.split()]
    content_words = [t for t in tokens if t and t not in _STOPWORDS]

    if not content_words:
        return 0.0

    ttr = len(set(content_words)) / len(content_words)
    return ttr * weights["lexical_diversity_weight"]


def half_boundary_bonus(half_text: str, weights: dict) -> float:
    """Return a bonus when a sentence half ends at a semicolon boundary.

    Semicolon-terminated Genji first halves consistently produce more
    natural-reading mashup pairs: the strong clause break gives the
    Quijote second half a clean entry point. Returns semicolon_half_bonus
    from weights if the half ends with ";", else 0.0.

    Parameters
    ----------
    half_text : str
        The displayed half-sentence text (after halving).
    weights : dict
        The "sentence" section of scoring_weights.json.

    Returns
    -------
    float
        The semicolon_half_bonus value, or 0.0.
    """
    if half_text.rstrip().endswith(";"):
        return weights.get("semicolon_half_bonus", 0.0)
    return 0.0


def score_sentence(
    sentence: str,
    detected_chars: list,
    registry: dict,
    weights: dict,
) -> float:
    """Score a sentence for lexical interestingness.

    Combines weighted scores for sentence length, character presence,
    place-name presence (detected via simple heuristics), and lexical
    diversity. Returns a raw float (not yet normalised to [0,1] — that
    happens across the full candidate pool in pair_generator).

    Parameters
    ----------
    sentence : str
        The cleaned sentence to score.
    detected_chars : list[str]
        Canonical character names detected in this sentence (from character_detector).
    registry : dict
        Source-specific subtree of character_ranks.json (the "genji" or "quijote" dict).
        Used to look up score_weight for each detected character.
    weights : dict
        The "sentence" section of scoring_weights.json.

    Returns
    -------
    float
        Raw score (sum of weighted components). Not normalised.
    """
    # Each component is already weighted internally by its respective weight
    # from the config. We sum them to get the final raw score.
    length_component = _length_score(sentence, weights) * weights["length_weight"]
    character_component = _character_score(detected_chars, registry, weights)
    place_component = _place_name_score(sentence, weights)
    diversity_component = _lexical_diversity_score(sentence, weights)

    return length_component + character_component + place_component + diversity_component

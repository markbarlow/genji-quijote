"""pair_generator.py — generate scored mashup pairs from Genji and Quijote sentence halves.

Implements the core pairing algorithm:
 1. Select top-K candidates from each pool (K = int(sqrt(count) * 10)).
 2. Generate all cross-product pairs from top-K genji × top-K quijote.
 3. Score each pair with score_pair().
 4. Sort descending by pair score and greedily select up to `count` pairs,
    enforcing uniqueness on the Genji full_sentence.
 5. Return a list of dicts matching the sentences.json schema.

All scores are normalised within each pool to [0, 1] before pairing, so
pair scores are comparable across runs with different input data.
"""

import math
from dataclasses import dataclass

from pipeline.pair_scorer import score_pair


# ---------------------------------------------------------------------------
# SentenceHalf dataclass
# ---------------------------------------------------------------------------


@dataclass
class SentenceHalf:
    """A single half of a split sentence, along with metadata.

    Attributes
    ----------
    half_text : str
        The text fragment that forms one half of the mashup display string.
    full_sentence : str
        The original cleaned sentence from which this half was derived
        (footnote markers already stripped). Used for source attribution
        and Genji uniqueness enforcement.
    chapter : str
        The chapter label (e.g. "CHAPTER I" or "V1 CHAPTER I.") from which
        the sentence was taken.
    sentence_index : int
        0-based index of the sentence within its chapter.
    half_strategy : str
        How the sentence was split: "clause_boundary" or "word_midpoint".
    detected_chars : list[str]
        Canonical character names found in the original full sentence.
    score : float
        Normalised score in [0, 1] representing sentence interestingness.
        Set by the pipeline after pool-level normalisation.
    source : str
        Either "genji" or "quijote".
    position : str
        Either "first" (Genji half — taken from the first half of the sentence)
        or "second" (Quijote half — taken from the second half).
    """

    half_text: str
    full_sentence: str
    chapter: str
    sentence_index: int
    half_strategy: str
    detected_chars: list
    score: float
    source: str
    position: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalise_scores(halves: list) -> list:
    """Return a copy of halves with scores normalised to [0, 1].

    Divides each score by the pool maximum so all values land in [0, 1].
    If the pool is empty or the maximum score is 0, scores are left as-is
    (all 0.0) to avoid a division-by-zero error.

    Parameters
    ----------
    halves : list[SentenceHalf]
        Pool of SentenceHalf objects to normalise.

    Returns
    -------
    list[SentenceHalf]
        New list of SentenceHalf objects with updated `score` values.
        The input list is not mutated.
    """
    if not halves:
        return halves

    max_score = max(h.score for h in halves)

    if max_score == 0.0:
        # Pool max is zero — all sentences score zero; return unchanged copies.
        return [
            SentenceHalf(
                half_text=h.half_text,
                full_sentence=h.full_sentence,
                chapter=h.chapter,
                sentence_index=h.sentence_index,
                half_strategy=h.half_strategy,
                detected_chars=h.detected_chars,
                score=h.score,
                source=h.source,
                position=h.position,
            )
            for h in halves
        ]

    return [
        SentenceHalf(
            half_text=h.half_text,
            full_sentence=h.full_sentence,
            chapter=h.chapter,
            sentence_index=h.sentence_index,
            half_strategy=h.half_strategy,
            detected_chars=h.detected_chars,
            score=h.score / max_score,  # normalise to [0, 1]
            source=h.source,
            position=h.position,
        )
        for h in halves
    ]


def _select_top_k(halves: list, count: int) -> list:
    """Return at most top-K halves sorted by score descending.

    K = int(sqrt(count) * 10), clamped to the full pool size.
    E.g. for count=50, K = int(7.07 * 10) = 70.

    Parameters
    ----------
    halves : list[SentenceHalf]
        Pool of normalised SentenceHalf objects.
    count : int
        Target output pair count, used to derive K.

    Returns
    -------
    list[SentenceHalf]
        Up to K halves, sorted by score descending.
    """
    k = int(math.sqrt(count) * 10)
    # Clamp K to the pool size so we never request more than we have.
    k = min(k, len(halves))
    # Sort descending by score; Python's sort is stable so ties preserve order.
    sorted_halves = sorted(halves, key=lambda h: h.score, reverse=True)
    return sorted_halves[:k]


# ---------------------------------------------------------------------------
# Conjunction double-up guard
# ---------------------------------------------------------------------------

# Words that, when appearing at the end of the Genji half AND the start of
# the Quijote half, create an awkward repeated conjunction ("...and and...").
_CONJUNCTIONS = {"and", "but", "yet", "or", "nor", "for", "so", "when", "while", "though"}


def _has_double_conjunction(genji_half: str, quijote_half: str) -> bool:
    """Return True if both halves share a conjunction at their join point.

    Detects cases like "...and [Quijote] and..." where the Genji half ends
    with a conjunction word and the Quijote half also starts with one,
    producing a grammatically broken double conjunction in the display.

    Parameters
    ----------
    genji_half : str
        The Genji first-half text.
    quijote_half : str
        The Quijote second-half text.

    Returns
    -------
    bool
        True if both boundary words are in the conjunction set.
    """
    genji_words = genji_half.rstrip().split()
    quijote_words = quijote_half.lstrip().split()
    if not genji_words or not quijote_words:
        return False
    # Strip trailing punctuation from the last Genji word before comparing.
    last_genji = genji_words[-1].lower().rstrip(".,;:")
    first_quijote = quijote_words[0].lower()
    return last_genji in _CONJUNCTIONS and first_quijote in _CONJUNCTIONS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_pairs(
    genji_halves: list,
    quijote_halves: list,
    count: int,
    weights: dict,
) -> list[dict]:
    """Generate scored mashup pairs from Genji first-halves and Quijote second-halves.

    Algorithm:
      1. Normalise scores within each pool to [0, 1] (divide by pool max).
      2. Select top-K from each pool where K = int(sqrt(count) * 10).
      3. Generate all cross-product pairs from top-K genji × top-K quijote.
      4. Score each pair using score_pair() from pair_scorer.
      5. Sort descending by pair score.
      6. Greedily select pairs, enforcing each Genji full_sentence appears
         at most once in the output, until `count` pairs are collected or
         the pool is exhausted.
      7. Return as a list of dicts matching the sentences.json schema.

    Parameters
    ----------
    genji_halves : list[SentenceHalf]
        First-half SentenceHalf objects (source="genji", position="first").
    quijote_halves : list[SentenceHalf]
        Second-half SentenceHalf objects (source="quijote", position="second").
    count : int
        Desired number of output pairs. May return fewer if the pool is
        exhausted before `count` unique-Genji pairs are found.
    weights : dict
        Full scoring_weights.json dict. The "pair" sub-dict is forwarded to
        score_pair() for mode bonus computation.

    Returns
    -------
    list[dict]
        Dicts conforming to the sentences.json pair schema. Each dict has:
        id, display, genji_half, quijote_half, genji_source, quijote_source,
        genji_chars, quijote_chars, score, mode, genji_meta, quijote_meta.
        Scores are rounded to 4 decimal places.
    """
    pair_weights = weights["pair"]

    # Step 1 — Normalise scores in each pool independently.
    genji_normalised = _normalise_scores(genji_halves)
    quijote_normalised = _normalise_scores(quijote_halves)

    # Step 2 — Select top-K from each normalised pool.
    top_genji = _select_top_k(genji_normalised, count)
    top_quijote = _select_top_k(quijote_normalised, count)

    # Step 3 — Generate all cross-product pairs and score each one.
    # We materialise the full cross product into a list so we can sort it.
    all_pairs = []
    for g in top_genji:
        for q in top_quijote:
            pair_score, mode = score_pair(
                g.score,
                q.score,
                g.detected_chars,
                q.detected_chars,
                pair_weights,
            )
            all_pairs.append((pair_score, mode, g, q))

    # Step 4 — Sort descending by pair score so greedy selection picks the best first.
    all_pairs.sort(key=lambda t: t[0], reverse=True)

    # Step 5 — Greedy selection with Genji uniqueness constraint.
    # Track which full_sentences have already been used on each side.
    # Both constraints are needed: without Quijote uniqueness the single
    # highest-scoring Quijote half wins every slot in the output.
    used_genji_sentences: set[str] = set()
    used_quijote_sentences: set[str] = set()
    selected = []

    for pair_score, mode, g, q in all_pairs:
        if len(selected) >= count:
            break
        if g.full_sentence in used_genji_sentences:
            continue
        if q.full_sentence in used_quijote_sentences:
            continue
        # Skip pairs where both halves have a conjunction at the join point
        # (e.g. "...and" + "and..." produces an incoherent double conjunction).
        if _has_double_conjunction(g.half_text, q.half_text):
            continue
        used_genji_sentences.add(g.full_sentence)
        used_quijote_sentences.add(q.full_sentence)
        selected.append((pair_score, mode, g, q))

    # Step 6 — Format selected pairs into the output schema.
    output = []
    for i, (pair_score, mode, g, q) in enumerate(selected, start=1):
        # ID is 1-based and zero-padded to 4 digits.
        pair_id = f"gq-{i:04d}"

        # display is the two halves joined with a single space.
        # The UI uses colour coding to distinguish Genji from Quijote.
        display = g.half_text + " " + q.half_text

        output.append({
            "id": pair_id,
            "display": display,
            "genji_half": g.half_text,
            "quijote_half": q.half_text,
            "genji_source": g.full_sentence,
            "quijote_source": q.full_sentence,
            "genji_chars": g.detected_chars,
            "quijote_chars": q.detected_chars,
            "score": round(pair_score, 4),
            "mode": mode,
            "genji_meta": {
                "chapter": g.chapter,
                "sentence_index": g.sentence_index,
                "half_strategy": g.half_strategy,
            },
            "quijote_meta": {
                "chapter": q.chapter,
                "sentence_index": q.sentence_index,
                "half_strategy": q.half_strategy,
            },
        })

    return output

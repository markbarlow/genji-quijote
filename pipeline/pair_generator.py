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
import warnings
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

    K = max(count, int(sqrt(count) * 10)), clamped to the full pool size.
    The sqrt term adds diversity headroom for small counts (e.g. count=50
    gives K=70 rather than 50). The max(count, ...) floor ensures K is always
    at least count, so generating N pairs is not artificially blocked by a
    cross-product that contains fewer than N unique halves.

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
    k = max(count, int(math.sqrt(count) * 10))
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

# Relative-clause openers: a Quijote half starting with any of these attaches
# to its own preceding clause — it cannot begin a sentence independently.
_RELATIVE_OPENERS = frozenset({"which", "whom", "whose"})

# Two-word sequences at the start of a Quijote half that signal a relative clause.
_RELATIVE_BIGRAMS = frozenset({"of whom", "in which", "by which", "to whom"})


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


def _has_seam_fault(genji_half: str, quijote_half: str) -> bool:
    """Return True if the pair has a grammatical seam fault at the join point.

    Checks three classes of fault:
      1. Double conjunction — both boundary words are conjunctions (delegated to
         _has_double_conjunction).
      2. Relative clause opener — the Quijote half begins with "which", "whom",
         "whose", or a relative bigram ("of whom", "in which", etc.), making it
         grammatically dependent on an antecedent that the Genji half lacks.
      3. Bare participle with no subject — the Quijote half starts with a present
         participle (word ending in "ing") and the Genji half contains no comma,
         meaning there is no preceding clause to attach the participial phrase to.

    Parameters
    ----------
    genji_half : str
        The Genji first-half text.
    quijote_half : str
        The Quijote second-half text.

    Returns
    -------
    bool
        True if the pair should be excluded from the output.
    """
    if _has_double_conjunction(genji_half, quijote_half):
        return True

    q_words = quijote_half.lstrip().split()
    if not q_words:
        return False

    first_q = q_words[0].lower().rstrip(".,;:")

    # Relative clause opener ("which he found", "whom he had seen", "whose horse")
    if first_q in _RELATIVE_OPENERS:
        return True

    # Relative bigram ("of whom he spoke", "in which Sancho slept")
    if len(q_words) >= 2:
        bigram = first_q + " " + q_words[1].lower().rstrip(".,;:")
        if bigram in _RELATIVE_BIGRAMS:
            return True

    # Bare present participle with no comma-anchored clause in the Genji half.
    # A participial phrase needs either a preceding comma or a clear subject clause;
    # we use the comma as a simple proxy.
    if first_q.endswith("ing") and "," not in genji_half:
        return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_pairs(
    genji_halves: list,
    quijote_halves: list,
    count: int,
    weights: dict,
    pinned_pairs: list[dict] | None = None,
) -> list[dict]:
    """Generate scored mashup pairs from Genji first-halves and Quijote second-halves.

    Algorithm:
      1. Normalise scores within each pool to [0, 1] (divide by pool max).
      2. Build full-pool text lookups so pinned pairs can be matched even if
         they fall below the top-K cutoff.
      3. Select top-K from each pool where K = int(sqrt(count) * 10).
      4. Generate all cross-product pairs from top-K genji × top-K quijote.
      5. Score each pair using score_pair() from pair_scorer.
      6. Sort descending by pair score.
      7. Force-include any pinned_pairs (matched by exact half text) at the
         start of the output; mark their sentences as used.
      8. Greedily select remaining pairs, enforcing each Genji full_sentence
         appears at most once in the output, until `count` pairs are collected
         or the pool is exhausted.
      9. Return as a list of dicts matching the sentences.json schema.

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
    pinned_pairs : list[dict] | None
        Optional list of {"genji_half": str, "quijote_half": str} dicts to
        force-include regardless of score. Matched against the full (non-top-K)
        pool by exact half text. Unmatched entries produce a warning and are
        skipped rather than raising an error.

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

    # Step 2 — Build full-pool text lookups before top-K slicing so that
    # pinned pairs can be matched even when their score falls below the cutoff.
    genji_by_text: dict[str, SentenceHalf] = {h.half_text: h for h in genji_normalised}
    quijote_by_text: dict[str, SentenceHalf] = {h.half_text: h for h in quijote_normalised}

    # Step 3 — Select top-K from each normalised pool.
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

    # Step 5 — Pre-seed the output with pinned pairs, force-including them
    # regardless of score.  Matched by exact half text against the full pool;
    # unmatched entries emit a warning and are skipped rather than raising.
    used_genji_sentences: set[str] = set()
    used_quijote_sentences: set[str] = set()
    selected = []

    if pinned_pairs:
        for pin in pinned_pairs:
            g = genji_by_text.get(pin["genji_half"])
            q = quijote_by_text.get(pin["quijote_half"])

            # If a half is not in the pool (sentence halved differently or
            # rejected by the weak-terminal filter), synthesise a SentenceHalf
            # directly from the pinned text so the pair is always force-included.
            # Optional fields in the pin ("genji_source", "genji_chapter", etc.)
            # are used to preserve source attribution for the UI reveal feature.
            if g is None:
                g = SentenceHalf(
                    half_text=pin["genji_half"],
                    full_sentence=pin.get("genji_source", pin["genji_half"]),
                    chapter=pin.get("genji_chapter", "pinned"),
                    sentence_index=0,
                    half_strategy="pinned",
                    detected_chars=[],
                    score=0.5,
                    source="genji",
                    position="first",
                )
            if q is None:
                q = SentenceHalf(
                    half_text=pin["quijote_half"],
                    full_sentence=pin.get("quijote_source", pin["quijote_half"]),
                    chapter=pin.get("quijote_chapter", "pinned"),
                    sentence_index=0,
                    half_strategy="pinned",
                    detected_chars=[],
                    score=0.5,
                    source="quijote",
                    position="second",
                )

            if g.full_sentence in used_genji_sentences or q.full_sentence in used_quijote_sentences:
                # Two pinned pairs share a source sentence — keep the first.
                warnings.warn(
                    f"[pinned_pairs] Skipping duplicate sentence: {pin['genji_half'][:40]!r}"
                )
                continue
            pair_score, mode = score_pair(
                g.score, q.score, g.detected_chars, q.detected_chars, pair_weights
            )
            used_genji_sentences.add(g.full_sentence)
            used_quijote_sentences.add(q.full_sentence)
            selected.append((pair_score, mode, g, q))

    # Step 6 — Greedy selection with Genji uniqueness constraint.
    # Track which full_sentences have already been used on each side.
    # Both constraints are needed: without Quijote uniqueness the single
    # highest-scoring Quijote half wins every slot in the output.
    for pair_score, mode, g, q in all_pairs:
        if len(selected) >= count:
            break
        if g.full_sentence in used_genji_sentences:
            continue
        if q.full_sentence in used_quijote_sentences:
            continue
        # Skip pairs with a grammatical seam fault at the join point
        # (double conjunction, relative clause opener, bare participle).
        if _has_seam_fault(g.half_text, q.half_text):
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

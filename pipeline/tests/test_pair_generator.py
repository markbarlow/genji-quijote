"""Unit tests for pipeline/pair_generator.py.

All tests use synthetic SentenceHalf objects — no source text files are read.
The test fixtures are designed to be small enough to reason about by hand
while still exercising the full pairing algorithm.
"""

import json
import pathlib

from pipeline.pair_generator import SentenceHalf, generate_pairs


# ---------------------------------------------------------------------------
# Load actual pair weights from config for realistic score assertions
# ---------------------------------------------------------------------------

_WEIGHTS_PATH = pathlib.Path(__file__).parents[2] / "config" / "scoring_weights.json"
with _WEIGHTS_PATH.open() as _f:
    _ALL_WEIGHTS = json.load(_f)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_genji(
    half_text: str,
    full_sentence: str,
    score: float,
    detected_chars: list | None = None,
    chapter: str = "CHAPTER I",
    sentence_index: int = 0,
) -> SentenceHalf:
    """Create a minimal genji SentenceHalf for testing.

    Parameters
    ----------
    half_text : str
        The half-sentence text fragment.
    full_sentence : str
        The full original sentence (used for uniqueness checking).
    score : float
        Raw score assigned to this half.
    detected_chars : list[str] | None
        Canonical character names; defaults to an empty list.
    chapter : str
        Chapter label; defaults to "CHAPTER I".
    sentence_index : int
        0-based index within the chapter; defaults to 0.

    Returns
    -------
    SentenceHalf
        A SentenceHalf with source="genji" and position="first".
    """
    return SentenceHalf(
        half_text=half_text,
        full_sentence=full_sentence,
        chapter=chapter,
        sentence_index=sentence_index,
        half_strategy="word_midpoint",
        detected_chars=detected_chars or [],
        score=score,
        source="genji",
        position="first",
    )


def _make_quijote(
    half_text: str,
    full_sentence: str,
    score: float,
    detected_chars: list | None = None,
    chapter: str = "CHAPTER I.",
    sentence_index: int = 0,
) -> SentenceHalf:
    """Create a minimal quijote SentenceHalf for testing.

    Parameters
    ----------
    half_text : str
        The half-sentence text fragment.
    full_sentence : str
        The full original sentence.
    score : float
        Raw score assigned to this half.
    detected_chars : list[str] | None
        Canonical character names; defaults to an empty list.
    chapter : str
        Chapter label; defaults to "CHAPTER I.".
    sentence_index : int
        0-based index within the chapter; defaults to 0.

    Returns
    -------
    SentenceHalf
        A SentenceHalf with source="quijote" and position="second".
    """
    return SentenceHalf(
        half_text=half_text,
        full_sentence=full_sentence,
        chapter=chapter,
        sentence_index=sentence_index,
        half_strategy="clause_boundary",
        detected_chars=detected_chars or [],
        score=score,
        source="quijote",
        position="second",
    )


def _make_pool(n: int, source: str, score_fn=None) -> list:
    """Generate a pool of n synthetic SentenceHalf objects.

    Each entry has a unique full_sentence and half_text so uniqueness checks
    work as expected. Scores are assigned by score_fn(i) if provided, else
    default to float(i) (incrementing integers, so item n-1 has the highest score).

    Parameters
    ----------
    n : int
        Number of SentenceHalf objects to create.
    source : str
        Either "genji" or "quijote".
    score_fn : callable | None
        Optional function (int -> float) mapping index to score.

    Returns
    -------
    list[SentenceHalf]
        Pool of synthetic halves.
    """
    make = _make_genji if source == "genji" else _make_quijote
    position = "first" if source == "genji" else "second"

    result = []
    for i in range(n):
        score = score_fn(i) if score_fn else float(i)
        result.append(
            make(
                half_text=f"{source}_half_{i} and more words here to fill the half text",
                full_sentence=f"{source}_sentence_{i}",
                score=score,
                sentence_index=i,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Required tests
# ---------------------------------------------------------------------------


def test_basic_pair_count():
    """generate_pairs returns exactly `count` pairs when the pool is large enough.

    Uses a 100 × 100 pool which easily satisfies the top-K selection and
    uniqueness constraint for count=50.
    """
    genji = _make_pool(100, "genji")
    quijote = _make_pool(100, "quijote")

    result = generate_pairs(genji, quijote, count=50, weights=_ALL_WEIGHTS)
    assert len(result) == 50, f"Expected 50 pairs, got {len(result)}"


def test_genji_uniqueness():
    """No two pairs share the same Genji full_sentence."""
    genji = []
    for i in range(5):
        for variant in ["a", "b"]:
            genji.append(
                _make_genji(
                    half_text=f"genji_half_{i}_{variant} with more words here",
                    full_sentence=f"shared_sentence_{i}",
                    score=float(i),
                )
            )

    quijote = _make_pool(20, "quijote")
    result = generate_pairs(genji, quijote, count=10, weights=_ALL_WEIGHTS)

    used = [pair["genji_source"] for pair in result]
    assert len(used) == len(set(used)), "Genji full_sentences must be unique across output pairs"


def test_quijote_uniqueness():
    """No two pairs share the same Quijote full_sentence.

    Without this constraint the single highest-scoring Quijote half would
    appear in every output pair, as it maximises (g_score + q_score) / 2
    for every Genji half.
    """
    genji = _make_pool(20, "genji")
    # All quijote halves share one of 3 full_sentences — ensures constraint is tested.
    quijote = []
    for i in range(3):
        for j in range(7):
            quijote.append(
                _make_quijote(
                    half_text=f"quijote_half_{i}_{j} with more words to fill",
                    full_sentence=f"shared_quijote_sentence_{i}",
                    score=float(i * 7 + j),
                )
            )

    result = generate_pairs(genji, quijote, count=10, weights=_ALL_WEIGHTS)

    used = [pair["quijote_source"] for pair in result]
    assert len(used) == len(set(used)), "Quijote full_sentences must be unique across output pairs"


def test_output_schema():
    """Each output dict contains all required keys with correct types and formats.

    Validates:
    - 'id' formatted as 'gq-NNNN' (4-digit zero-padded)
    - 'display' == genji_half + quijote_half with no separator
    - All required keys are present
    """
    genji = _make_pool(30, "genji")
    quijote = _make_pool(30, "quijote")

    result = generate_pairs(genji, quijote, count=5, weights=_ALL_WEIGHTS)

    required_keys = {
        "id", "display", "genji_half", "quijote_half",
        "genji_source", "quijote_source", "genji_chars", "quijote_chars",
        "score", "mode", "genji_meta", "quijote_meta",
    }
    meta_keys = {"chapter", "sentence_index", "half_strategy"}

    for i, pair in enumerate(result, start=1):
        assert required_keys.issubset(pair.keys()), (
            f"Pair {i} missing keys: {required_keys - pair.keys()}"
        )

        # ID format check
        assert pair["id"] == f"gq-{i:04d}", (
            f"Expected id='gq-{i:04d}', got '{pair['id']}'"
        )

        # display is genji_half + quijote_half with NO separator
        expected_display = pair["genji_half"] + pair["quijote_half"]
        assert pair["display"] == expected_display, (
            f"display does not equal genji_half + quijote_half for pair {i}"
        )

        # Meta sub-dicts
        assert meta_keys.issubset(pair["genji_meta"].keys()), "genji_meta missing keys"
        assert meta_keys.issubset(pair["quijote_meta"].keys()), "quijote_meta missing keys"

        # Type checks
        assert isinstance(pair["score"], float), "score must be float"
        assert isinstance(pair["mode"], str), "mode must be str"
        assert isinstance(pair["genji_chars"], list), "genji_chars must be list"
        assert isinstance(pair["quijote_chars"], list), "quijote_chars must be list"


def test_top_k_selection():
    """With a large pool and small count, returned pairs use only the highest-scoring halves.

    Assigns scores so that items 0..49 have low scores (0.0..49.0) and
    items 50..99 have high scores (50.0..99.0). With count=5, K = int(√5 * 10) = 22,
    so only the top-22 genji halves (indices 78-99) should appear in the output.
    All returned genji halves must have raw scores >= 78.0.
    """
    n = 100
    # Scores are just the index: highest scores are at the end of the list
    genji = _make_pool(n, "genji", score_fn=lambda i: float(i))
    quijote = _make_pool(n, "quijote", score_fn=lambda i: float(i))

    result = generate_pairs(genji, quijote, count=5, weights=_ALL_WEIGHTS)

    # K for count=5 is int(sqrt(5) * 10) = int(2.236 * 10) = 22
    # So only the top 22 genji (indices 78..99) should be selected.
    # The minimum score in the top-22 is 78.0 (raw, before normalisation).
    # After normalisation, the minimum normalised score in top-K is 78/99 ≈ 0.788.
    # We verify by checking the genji_source — top-22 genji have sentence_index >= 78.
    for pair in result:
        # Extract the index from the synthetic full_sentence name "genji_sentence_N"
        genji_idx = int(pair["genji_source"].split("_")[-1])
        assert genji_idx >= 78, (
            f"Genji half with index {genji_idx} should not appear in top-K for count=5 "
            f"(expected index >= 78)"
        )


def test_smaller_pool_than_count():
    """When the pool has fewer unique Genji sentences than count, return as many as possible.

    Uses a pool of 5 unique Genji sentences and requests 20 pairs. The function
    must return at most 5 pairs without raising any error.
    """
    genji = _make_pool(5, "genji")
    quijote = _make_pool(30, "quijote")

    result = generate_pairs(genji, quijote, count=20, weights=_ALL_WEIGHTS)

    # Cannot exceed pool size; must not error
    assert len(result) <= 5, f"Expected at most 5 pairs, got {len(result)}"
    assert len(result) > 0, "Expected at least one pair"


def test_score_rounded():
    """Scores in output are rounded to exactly 4 decimal places.

    Constructs pairs that will produce non-terminating scores and checks
    that the 'score' field has at most 4 decimal digits.
    """
    genji = _make_pool(20, "genji", score_fn=lambda i: i / 3.0)
    quijote = _make_pool(20, "quijote", score_fn=lambda i: i / 7.0)

    result = generate_pairs(genji, quijote, count=5, weights=_ALL_WEIGHTS)

    for pair in result:
        score = pair["score"]
        # Round to 4 dp and compare: the stored value should equal itself rounded
        assert score == round(score, 4), (
            f"Score {score} is not rounded to 4 decimal places"
        )
        # Also verify precision by checking string representation has <= 4 dp
        score_str = str(score)
        if "." in score_str:
            decimal_part = score_str.split(".")[1]
            assert len(decimal_part) <= 4, (
                f"Score {score} has more than 4 decimal places: {score_str}"
            )


def test_mode_classification():
    """Pairs with named characters on both sides get mode 'character_encounter'.

    Constructs a single genji half with characters and a single quijote half
    with characters, then checks that the output mode is 'character_encounter'.
    """
    g = _make_genji(
        half_text="the prince gazed at the moonlit garden in silence",
        full_sentence="the prince gazed at the moonlit garden in silence and sighed.",
        score=0.9,
        detected_chars=["Genji"],
    )
    q = _make_quijote(
        half_text="rode forth on Rocinante into the wide plain",
        full_sentence="Don Quixote rode forth on Rocinante into the wide plain.",
        score=0.9,
        detected_chars=["Don_Quixote"],
    )

    result = generate_pairs([g], [q], count=1, weights=_ALL_WEIGHTS)

    assert len(result) == 1, "Expected exactly 1 pair"
    assert result[0]["mode"] == "character_encounter", (
        f"Expected mode='character_encounter', got '{result[0]['mode']}'"
    )
    # Sanity-check chars are propagated correctly
    assert result[0]["genji_chars"] == ["Genji"]
    assert result[0]["quijote_chars"] == ["Don_Quixote"]


def test_empty_pools():
    """generate_pairs returns an empty list when either pool is empty.

    The function must not raise when given an empty genji or quijote pool.
    """
    genji = _make_pool(10, "genji")
    quijote = []

    result = generate_pairs(genji, quijote, count=5, weights=_ALL_WEIGHTS)
    assert result == [], "Expected empty list when quijote pool is empty"

    result2 = generate_pairs([], _make_pool(10, "quijote"), count=5, weights=_ALL_WEIGHTS)
    assert result2 == [], "Expected empty list when genji pool is empty"

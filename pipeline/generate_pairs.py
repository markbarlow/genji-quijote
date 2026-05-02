"""generate_pairs.py — CLI entry point for the Genji–Quijote mashup pipeline.

Orchestrates the full pipeline in sequence:
  1. Load config files (character_ranks, scoring_weights, ignore_patterns)
  2. Load source texts
  3. Clean each text (strip Gutenberg wrapper, footnotes, tag chapters)
  4. Sentence-split each chapter body via spaCy
  5. Filter sentences
  6. Halve each sentence
  7. Detect characters and compute raw sentence scores
  8. Build SentenceHalf objects and normalise scores within each pool
  9. Generate pairs via pair_generator.generate_pairs()
  10. Write sentences.json with the meta envelope

All progress messages are written to stderr so stdout remains clean.

Usage:
    python pipeline/generate_pairs.py --count 1021 --output sentences.json
    python pipeline/generate_pairs.py --count 50 --output dev_sample.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import spacy

from pipeline.character_detector import detect_characters
from pipeline.pair_generator import SentenceHalf, generate_pairs
from pipeline.sentence_filter import filter_sentences
from pipeline.sentence_halver import halve_sentence
from pipeline.sentence_scorer import half_boundary_bonus, score_sentence
from pipeline.sentence_splitter import split_sentences
from pipeline.text_cleaner import (
    remove_footnote_definitions,
    strip_genji_footnote_markers,
    strip_gutenberg_wrapper,
    tag_chapter_headings,
)
from pipeline.text_loader import load_text


# ---------------------------------------------------------------------------
# Repo root: resolve relative to this file so the CLI works from any cwd
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent


def _load_config() -> tuple[dict, dict, dict]:
    """Load all three config files from config/ and return them as dicts.

    Returns
    -------
    tuple[dict, dict, dict]
        (character_ranks, scoring_weights, ignore_patterns)
    """
    char_ranks_path = _REPO_ROOT / "config" / "character_ranks.json"
    weights_path = _REPO_ROOT / "config" / "scoring_weights.json"
    ignore_path = _REPO_ROOT / "config" / "ignore_patterns.json"

    with char_ranks_path.open(encoding="utf-8") as f:
        character_ranks = json.load(f)
    with weights_path.open(encoding="utf-8") as f:
        scoring_weights = json.load(f)
    with ignore_path.open(encoding="utf-8") as f:
        ignore_patterns = json.load(f)

    return character_ranks, scoring_weights, ignore_patterns


def _clean_genji(raw_text: str) -> str:
    """Apply the full Genji cleaning pipeline to the raw source text.

    Strips the Gutenberg wrapper, removes inline footnote markers, and
    removes footnote definition lines. The result is ready for chapter
    tagging and sentence splitting.

    Parameters
    ----------
    raw_text : str
        Raw UTF-8 text from text_loader.load_text().

    Returns
    -------
    str
        Cleaned body text.
    """
    text = strip_gutenberg_wrapper(raw_text)
    text = strip_genji_footnote_markers(text)
    text = remove_footnote_definitions(text)
    return text


def _clean_quijote(raw_text: str) -> str:
    """Apply the full Quijote cleaning pipeline to the raw source text.

    Strips the Gutenberg wrapper only — Quijote has no footnote markers
    or definition lines to remove.

    Parameters
    ----------
    raw_text : str
        Raw UTF-8 text from text_loader.load_text().

    Returns
    -------
    str
        Cleaned body text.
    """
    return strip_gutenberg_wrapper(raw_text)


def _process_source(
    source: str,
    cleaned_text: str,
    position: str,
    nlp,
    ignore_config: dict,
    halving_config: dict,
    character_registry: dict,
    sentence_weights: dict,
) -> list[SentenceHalf]:
    """Run the full per-sentence pipeline for one source text and return SentenceHalf objects.

    Processes each chapter in sequence:
      - Split body text into sentences via spaCy
      - Filter sentences via sentence_filter
      - Halve each sentence via sentence_halver
      - Detect characters and score each half

    Rejected halves (halve_sentence returns None) are silently skipped.

    Parameters
    ----------
    source : str
        Either "genji" or "quijote". Must match the keys in config dicts.
    cleaned_text : str
        Cleaned body text (Gutenberg wrapper and footnotes already removed).
    position : str
        "first" for Genji (we take the first half) or "second" for Quijote
        (we take the second half).
    nlp : spacy.Language
        Loaded spaCy language model (shared across both sources).
    ignore_config : dict
        Full ignore_patterns.json dict. Forwarded to filter_sentences.
    halving_config : dict
        Dict with a "halving" sub-key. Forwarded to halve_sentence.
    character_registry : dict
        Source-specific subtree of character_ranks.json (already sliced to
        character_ranks[source]).
    sentence_weights : dict
        The "sentence" sub-dict of scoring_weights.json.

    Returns
    -------
    list[SentenceHalf]
        All valid SentenceHalf objects extracted from the source text, in
        document order. Scores are raw (not yet normalised across the pool).
    """
    # Tag chapters so each sentence can carry a chapter label in its metadata.
    chapters = tag_chapter_headings(cleaned_text, source)

    halves: list[SentenceHalf] = []

    for chapter_label, chapter_body in chapters:
        # Split the chapter body into raw sentences using spaCy.
        raw_sentences = split_sentences(chapter_body, nlp)

        # Filter sentences by length and pattern rules.
        filtered = filter_sentences(raw_sentences, source, ignore_config)

        for sentence_index, sentence in enumerate(filtered):
            # Halve the sentence at a clause boundary (or word midpoint as fallback).
            first_half, second_half, strategy = halve_sentence(sentence, halving_config)

            # Skip rejected sentences (too short to split into valid halves).
            if strategy == "rejected":
                continue

            # Select which half this source contributes to mashup pairs.
            half_text = first_half if position == "first" else second_half

            # Detect named characters in the full sentence.
            # We run detection on the full sentence (not just the half) so
            # character metadata is accurate even when the name appears in the
            # other half.
            detected_chars = detect_characters(sentence, character_registry)

            # Score the full sentence — normalisation happens later across the pool.
            raw_score = score_sentence(sentence, detected_chars, character_registry, sentence_weights)

            # For Genji first halves, apply a bonus when the half ends at a
            # semicolon — these splits produce cleaner joins with the Quijote half.
            if position == "first":
                raw_score += half_boundary_bonus(half_text, sentence_weights)

            halves.append(
                SentenceHalf(
                    half_text=half_text,
                    full_sentence=sentence,
                    chapter=chapter_label,
                    sentence_index=sentence_index,
                    half_strategy=strategy,
                    detected_chars=detected_chars,
                    score=raw_score,
                    source=source,
                    position=position,
                )
            )

    return halves


def _build_output(pairs: list[dict]) -> dict:
    """Wrap the pairs list in the sentences.json meta envelope.

    Parameters
    ----------
    pairs : list[dict]
        Output from generate_pairs(), already schema-compliant.

    Returns
    -------
    dict
        Top-level sentences.json dict with "meta" and "pairs" keys.
    """
    return {
        "meta": {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(pairs),
            # window_size controls the Fisher-Yates depletion queue in the frontend.
            "window_size": 30,
        },
        "pairs": pairs,
    }


def main() -> None:
    """Parse CLI arguments and run the full pipeline, writing sentences.json.

    Returns
    -------
    None
        Exits with code 0 on success. Writes output JSON to the specified path.
    """
    parser = argparse.ArgumentParser(
        description="Generate Genji–Quijote mashup sentence pairs."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1021,
        help="Number of pairs to generate (default: 1021).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="sentences.json",
        help="Output file path (default: sentences.json).",
    )
    args = parser.parse_args()

    count: int = args.count
    output_path = Path(args.output)

    print(f"[generate_pairs] Target: {count} pairs → {output_path}", file=sys.stderr)

    # Step 1 — Load config files.
    print("[generate_pairs] Loading config...", file=sys.stderr)
    character_ranks, scoring_weights, ignore_patterns = _load_config()

    sentence_weights = scoring_weights["sentence"]
    # sentence_halver.py expects {"halving": {...}} as its config dict.
    # The halving parameters live in scoring_weights.json under the "halving" key.
    halving_config = {"halving": scoring_weights["halving"]}

    # Step 2 — Load source texts.
    print("[generate_pairs] Loading source texts...", file=sys.stderr)
    genji_path = _REPO_ROOT / "source-materials" / "gutenberg-source-text" / "the-tale-of-genji-complete.txt"
    quijote_path = _REPO_ROOT / "source-materials" / "gutenberg-source-text" / "don-quijote-volume-1-volume-2.txt"

    genji_raw = load_text(genji_path)
    quijote_raw = load_text(quijote_path)

    # Step 3 — Clean texts.
    print("[generate_pairs] Cleaning texts...", file=sys.stderr)
    genji_cleaned = _clean_genji(genji_raw)
    quijote_cleaned = _clean_quijote(quijote_raw)

    # Step 4 — Load spaCy model once (shared across both sources for efficiency).
    print("[generate_pairs] Loading spaCy model...", file=sys.stderr)
    nlp = spacy.load("en_core_web_sm")

    # Steps 4–7 — Sentence split, filter, halve, detect, score for each source.
    print("[generate_pairs] Processing Genji sentences...", file=sys.stderr)
    genji_halves = _process_source(
        source="genji",
        cleaned_text=genji_cleaned,
        position="first",
        nlp=nlp,
        ignore_config=ignore_patterns,
        halving_config=halving_config,
        character_registry=character_ranks["genji"],
        sentence_weights=sentence_weights,
    )
    print(f"[generate_pairs] Genji halves: {len(genji_halves)}", file=sys.stderr)

    print("[generate_pairs] Processing Quijote sentences...", file=sys.stderr)
    quijote_halves = _process_source(
        source="quijote",
        cleaned_text=quijote_cleaned,
        position="second",
        nlp=nlp,
        ignore_config=ignore_patterns,
        halving_config=halving_config,
        character_registry=character_ranks["quijote"],
        sentence_weights=sentence_weights,
    )
    print(f"[generate_pairs] Quijote halves: {len(quijote_halves)}", file=sys.stderr)

    # Step 9 — Load pinned pairs and generate scored pairs.
    # Normalisation of scores within each pool is handled inside generate_pairs().
    pinned_path = _REPO_ROOT / "config" / "pinned_pairs.json"
    pinned_pairs: list[dict] = []
    if pinned_path.exists():
        with pinned_path.open(encoding="utf-8") as f:
            pinned_data = json.load(f)
        pinned_pairs = pinned_data.get("pairs", [])
        print(f"[generate_pairs] Loaded {len(pinned_pairs)} pinned pairs.", file=sys.stderr)

    print(f"[generate_pairs] Generating {count} pairs...", file=sys.stderr)
    pairs = generate_pairs(
        genji_halves, quijote_halves, count=count, weights=scoring_weights,
        pinned_pairs=pinned_pairs,
    )
    print(f"[generate_pairs] Generated {len(pairs)} pairs.", file=sys.stderr)

    # Step 10 — Write output JSON.
    output = _build_output(pairs)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[generate_pairs] Written to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

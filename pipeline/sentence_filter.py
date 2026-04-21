"""sentence_filter.py — filter sentences by length, pattern, and quality heuristics.

This module provides a single responsibility: given a list of sentence strings,
a source name, and a config dict, return a filtered list. No NLP calls—purely
string-based filtering using regex patterns and word counts.

Filters applied in sequence:
1. Skip blank/whitespace-only sentences
2. Skip sentences matching source-specific regex patterns
3. Skip sentences below min word count
4. Skip sentences above max word count
5. For quijote only: skip sentences matching Latin heuristic pattern
6. Skip all-caps sentences (heading remnants)
"""

import re


def filter_sentences(sentences: list[str], source: str, config: dict) -> list[str]:
    """Filter sentences, removing those that are too short, too long, or match ignore patterns.

    Applies six filters in sequence:
    1. Skip blank/whitespace-only sentences
    2. Skip sentences matching source-specific regex patterns
    3. Skip sentences below min_tokens
    4. Skip sentences above max_tokens
    5. For quijote only: skip sentences matching Latin heuristic pattern
    6. Skip all-caps sentences (3+ words and all uppercase—targets heading remnants)

    Parameters
    ----------
    sentences : list[str]
        Raw sentences from sentence_splitter.
    source : str
        Either 'genji' or 'quijote'. Selects the source-specific config section.
    config : dict
        Configuration dict matching the structure of config/ignore_patterns.json.
        Expected structure:
        {
            "genji": {
                "sentence_patterns": [...],  # list of regex patterns (str or compiled)
                "min_tokens": int,
                "max_tokens": int
            },
            "quijote": {
                "sentence_patterns": [...],
                "latin_pattern": str or compiled regex (optional),
                "min_tokens": int,
                "max_tokens": int
            }
        }

    Returns
    -------
    list[str]
        Sentences that passed all filters.
    """
    source_config = config[source]
    min_tokens = source_config["min_tokens"]
    max_tokens = source_config["max_tokens"]
    sentence_patterns = source_config["sentence_patterns"]

    # Compile regex patterns if they're strings (in case config came from JSON)
    compiled_patterns = []
    for pattern in sentence_patterns:
        if isinstance(pattern, str):
            compiled_patterns.append(re.compile(pattern))
        else:
            compiled_patterns.append(pattern)

    # Compile latin_regex once (Critical 1: avoid recompilation in loop)
    # For quijote only; None for genji
    latin_regex = None
    if source == "quijote":
        latin_pattern = source_config.get("latin_pattern")
        if latin_pattern:
            if isinstance(latin_pattern, str):
                latin_regex = re.compile(latin_pattern)
            else:
                latin_regex = latin_pattern

    filtered = []

    for sentence in sentences:
        # Filter 1: Skip blank/whitespace-only sentences
        if not sentence or not sentence.strip():
            continue

        # Filter 2: Skip sentences matching source-specific patterns
        if any(pattern.search(sentence) for pattern in compiled_patterns):
            continue

        # Word count for filters 3 and 4 (split on whitespace)
        word_count = len(sentence.split())

        # Filter 3: Skip sentences below min_tokens
        if word_count < min_tokens:
            continue

        # Filter 4: Skip sentences above max_tokens
        if word_count > max_tokens:
            continue

        # Filter 5: For quijote only, skip sentences matching Latin heuristic
        if latin_regex and latin_regex.search(sentence):
            continue

        # Filter 6: Skip all-caps sentences (heading remnants)
        # Only apply to multi-word sentences (3+ words) to avoid filtering exclamations
        # like "I" which are too short anyway (filtered by min_tokens) but should
        # not be the reason for rejection
        if len(sentence.split()) >= 3 and sentence.strip().isupper():
            continue

        # Sentence passed all filters
        filtered.append(sentence)

    return filtered

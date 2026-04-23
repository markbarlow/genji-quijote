"""Character detection module for literary text processing.

Detects which named characters appear in a sentence using whole-word,
case-insensitive matching. Character information is used for scoring
and for classifying sentence pairs as "character_encounter" types.
"""

import re


def detect_characters(sentence: str, registry: dict) -> list[str]:
    """Detect which canonical character names appear in a sentence.

    Searches for each character's canonical name and all its variants using
    whole-word matching (so "Sancho" does not match "Sanchopanza"). Returns
    canonical names only — not variant strings.

    Parameters
    ----------
    sentence : str
        The sentence to search. Case-insensitive matching is used.
    registry : dict
        The source-specific subtree of character_ranks.json — i.e. the dict
        under "genji" or "quijote". Keys are canonical names; values are dicts
        with "rank", "variants", and "score_weight".

    Returns
    -------
    list[str]
        Canonical names of detected characters, in the order they appear in
        the registry. No duplicates. Empty list if no characters detected.
    """
    detected = []

    for canonical_key, char_data in registry.items():
        # Build list of all names to search for: canonical (with underscores
        # replaced by spaces) and all variants.
        # The canonical key uses underscores for spaces (e.g. "Don_Quixote"),
        # but the source text contains spaces, so we search for the spaced version.
        canonical_spaced = canonical_key.replace("_", " ")
        names_to_search = [canonical_spaced]

        # Add all variants from the registry
        variants = char_data.get("variants", [])
        if variants:
            names_to_search.extend(variants)

        # Compile all patterns once before scanning the sentence.
        # Pre-compilation avoids rebuilding the regex engine state on every name check,
        # which matters when detect_characters is called for thousands of sentences.
        compiled = [
            re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
            for name in names_to_search
        ]

        # Search for any match (canonical or variant) using whole-word boundaries
        for pattern in compiled:
            if pattern.search(sentence):
                # Found a match: add canonical key (with underscores preserved)
                # and break to avoid duplicates
                detected.append(canonical_key)
                break

    return detected

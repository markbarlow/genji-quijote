"""Pair scoring module for literary sentence mashups.

Combines pre-computed sentence scores from the Genji and Quijote halves,
applies a mode-based bonus for character co-presence, and classifies each
pair as one of three narrative modes:

  character_encounter — both halves contain at least one named character
  character_named     — exactly one half contains a named character
  standard            — neither half contains a named character
"""


def _classify_mode(genji_chars: list, quijote_chars: list) -> str:
    """Determine the narrative mode of a pair based on character presence.

    Parameters
    ----------
    genji_chars : list[str]
        Character names detected in the Genji half.
    quijote_chars : list[str]
        Character names detected in the Quijote half.

    Returns
    -------
    str
        One of "character_encounter", "character_named", or "standard".
    """
    genji_has = len(genji_chars) > 0
    quijote_has = len(quijote_chars) > 0

    if genji_has and quijote_has:
        # Both sides feature named characters — the most dramatically resonant mode.
        return "character_encounter"
    if genji_has or quijote_has:
        # Exactly one side has a character — a named-character moment.
        return "character_named"
    # Neither side contains a named character — plain descriptive prose.
    return "standard"


def score_pair(
    genji_score: float,
    quijote_score: float,
    genji_chars: list,
    quijote_chars: list,
    pair_weights: dict,
) -> tuple[float, str]:
    """Score a sentence pair and classify its mode.

    Computes the base score as the arithmetic mean of the two sentence scores,
    then adds a mode-dependent bonus from pair_weights. The bonus rewards pairs
    where one or both halves feature named characters, since such pairs tend to
    produce more narratively interesting mashups.

    Parameters
    ----------
    genji_score : float
        Pre-computed score for the Genji half-sentence.
    quijote_score : float
        Pre-computed score for the Quijote half-sentence.
    genji_chars : list[str]
        Character names detected in the Genji half.
    quijote_chars : list[str]
        Character names detected in the Quijote half.
    pair_weights : dict
        The "pair" section of scoring_weights.json.

    Returns
    -------
    tuple[float, str]
        (pair_score, mode) where mode is one of:
        "character_encounter" — both halves have at least one detected character
        "character_named"     — exactly one half has a detected character
        "standard"            — neither half has a detected character
    """
    mode = _classify_mode(genji_chars, quijote_chars)

    # Average the two sentence scores to form the base pair score.
    # Using the mean (rather than sum) keeps the pair score on the same
    # rough scale as the individual sentence scores.
    base = (genji_score + quijote_score) / 2.0

    # Apply a bonus proportional to how "character-rich" the pairing is.
    if mode == "character_encounter":
        bonus = pair_weights["character_encounter_bonus"]
    elif mode == "character_named":
        bonus = pair_weights["character_named_bonus"]
    else:
        # Standard mode: no bonus
        bonus = 0.0

    pair_score = base + bonus
    return float(pair_score), mode

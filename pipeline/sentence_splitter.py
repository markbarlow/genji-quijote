"""sentence_splitter.py — split cleaned text into individual sentences.

This module provides a single responsibility: given chapter body text and a
loaded spaCy model, return a list of sentence strings.

The input text should already be cleaned (Gutenberg boilerplate and footnote
markers/definitions removed) by text_cleaner.py. The spaCy model is injected
so callers control loading and tests can substitute lightweight mocks.
"""


def split_sentences(text: str, nlp) -> list[str]:
    """Split text into sentences using spaCy's sentence segmentation.

    Parameters
    ----------
    text : str
        Chapter body text to segment. Should already be cleaned (footnote
        markers and definitions removed).
    nlp : spacy.Language
        Loaded spaCy language model. Passed in (not loaded internally) so
        callers control model loading and tests can substitute a lightweight
        model or mock.

    Returns
    -------
    list[str]
        Sentences as stripped strings. Empty strings are excluded.
    """
    # Process text through spaCy to obtain a Doc with sentence boundaries
    doc = nlp(text)

    # Extract sentence text from each spaCy Sent object, strip whitespace,
    # and filter out empty strings
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    return sentences

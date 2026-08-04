"""Compares a submitted answer against a clue's accepted answers/synonyms.
Tolerant of case, extra whitespace, and small spelling variations (typo-level
edit distance) via rapidfuzz — without being so loose that wrong answers slip
through."""

import re

from rapidfuzz import fuzz

# similarity threshold (0-100) for accepting a near-miss as correct
FUZZY_THRESHOLD = 88


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)  # drop punctuation
    return text


def is_correct(submitted: str, accepted_answers: list[str]) -> bool:
    """accepted_answers should already include any synonyms the admin configured
    for this clue — this function does not fetch synonyms itself."""
    candidate = _normalize(submitted)
    if not candidate:
        return False

    for answer in accepted_answers:
        target = _normalize(answer)
        if candidate == target:
            return True
        if fuzz.ratio(candidate, target) >= FUZZY_THRESHOLD:
            return True
    return False

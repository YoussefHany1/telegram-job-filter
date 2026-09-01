"""
filters/rules.py

Pure, side-effect-free matching primitives. No Telegram, no database - just
strings in, results out. This is what Phase 10's unit tests exercise
directly, and what filters/engine.py composes into the full pipeline.
"""

from __future__ import annotations

from enum import Enum

from filters.normalizer import normalize_text


class MatchMode(str, Enum):
    OR = "OR"
    AND = "AND"


def find_matched_keywords(normalized_text: str, keywords: list[str]) -> list[str]:
    """Return the subset of `keywords` (original casing/spelling as given)
    found inside `normalized_text`. Each keyword is normalized the same way
    the message text was, so matching stays case-insensitive and
    Unicode-safe for Arabic/English/mixed input alike."""
    matched: list[str] = []
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword, strip_urls=False)
        if normalized_keyword and normalized_keyword in normalized_text:
            matched.append(keyword)
    return matched


def includes_match(
    normalized_text: str,
    include_keywords: list[str],
    mode: MatchMode = MatchMode.OR,
) -> tuple[bool, list[str]]:
    """
    OR mode  -> matches if ANY include keyword is found.
    AND mode -> matches only if ALL include keywords are found.
    No include keywords configured -> never matches (nothing to forward),
    rather than silently forwarding everything.
    """
    if not include_keywords:
        return False, []

    matched = find_matched_keywords(normalized_text, include_keywords)

    if mode == MatchMode.AND:
        return len(matched) == len(include_keywords), matched
    return len(matched) > 0, matched


def excludes_match(normalized_text: str, exclude_keywords: list[str]) -> list[str]:
    """Exclude keywords always work as OR: any single match is enough to
    reject the message. Returns the matched exclude keyword(s)."""
    return find_matched_keywords(normalized_text, exclude_keywords)

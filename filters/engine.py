"""
filters/engine.py

Composes normalizer + rules into the single entry point the listener calls:
`FilterEngine.evaluate(original_text)`. Everything below the surface is
swappable (matching mode, keyword sources) without the caller changing.

Modular by design: `evaluate()` takes plain include/exclude keyword lists
and a mode, so a future keyword-groups feature (Section 18) can call it
once per group with different lists, or a caller can pass a merged list -
this function doesn't know or care where the lists came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from filters.normalizer import normalize_text
from filters.rules import MatchMode, excludes_match, includes_match


@dataclass(frozen=True)
class FilterResult:
    matched: bool
    normalized_text: str
    matched_include_keywords: list[str] = field(default_factory=list)
    matched_exclude_keywords: list[str] = field(default_factory=list)
    reason: str = ""


class FilterEngine:
    def evaluate(
        self,
        original_text: str,
        include_keywords: list[str],
        exclude_keywords: list[str],
        mode: MatchMode = MatchMode.OR,
    ) -> FilterResult:
        normalized = normalize_text(original_text)

        included, matched_includes = includes_match(normalized, include_keywords, mode)
        if not included:
            return FilterResult(
                matched=False,
                normalized_text=normalized,
                reason="no_include_match",
            )

        matched_excludes = excludes_match(normalized, exclude_keywords)
        if matched_excludes:
            return FilterResult(
                matched=False,
                normalized_text=normalized,
                matched_include_keywords=matched_includes,
                matched_exclude_keywords=matched_excludes,
                reason="excluded",
            )

        return FilterResult(
            matched=True,
            normalized_text=normalized,
            matched_include_keywords=matched_includes,
            reason="matched",
        )

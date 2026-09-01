"""
filters/normalizer.py

Preprocessing layer used before any keyword matching. Produces a
`normalized_text` used only for matching - the `original_text` handed to
the message formatter (Phase 6) is never touched by this module.

Unicode / Arabic notes
-----------------------
- NFKC normalization folds compatibility characters (e.g. Arabic presentation
  forms, full-width Latin letters) into their canonical form, so the same
  visual word typed differently still compares equal.
- `str.lower()` is a no-op on Arabic (it has no case) and correctly
  lowercases Latin/Cyrillic/etc, so it's safe to always apply.
- We deliberately do NOT strip Arabic diacritics (tashkeel) or normalize
  alef/yaa variants beyond what NFKC already does - that's a heavier,
  optional step that can be added later without changing this module's
  interface if false negatives on Arabic text turn out to be a problem.
"""

from __future__ import annotations

import re
import unicodedata

_URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
# Punctuation/symbols that commonly separate words in job posts without
# carrying meaning for keyword matching (keeps letters/digits/marks/spaces
# from all scripts, including Arabic, intact).
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_text(text: str, *, strip_urls: bool = True) -> str:
    """Return a lowercase, whitespace-collapsed, Unicode-normalized copy of
    `text` suitable for keyword matching. Never mutates or returns the
    original object's formatting - callers keep their own original_text."""
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.lower()

    if strip_urls:
        normalized = _URL_RE.sub(" ", normalized)

    normalized = _PUNCTUATION_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized

"""
tests/test_normalizer.py

Unit tests for filters/normalizer.py: lowercasing, whitespace/punctuation
collapsing, URL stripping, and the "original text stays untouched" rule
(Section 8).
"""

from filters.normalizer import normalize_text


def test_lowercases():
    assert normalize_text("REACT Native") == "react native"


def test_collapses_whitespace_and_newlines():
    assert normalize_text("React   Native\n\nDeveloper") == "react native developer"


def test_strips_urls_by_default():
    normalized = normalize_text("Apply at https://example.com/job now")
    assert "example.com" not in normalized
    assert "apply at" in normalized
    assert "now" in normalized


def test_can_keep_urls_when_disabled():
    # Punctuation (including dots/slashes) is still stripped either way -
    # `strip_urls` only controls whether the URL is removed *entirely*.
    normalized = normalize_text("Apply at https://example.com/job now", strip_urls=False)
    assert "example com" in normalized


def test_original_text_is_never_mutated():
    original = "  React Native, Remote!  "
    normalize_text(original)
    assert original == "  React Native, Remote!  "


def test_empty_and_none_safe():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


def test_arabic_text_is_unicode_safe():
    normalized = normalize_text("مطلوب مطور React Native")
    assert "مطور" in normalized
    assert "react native" in normalized

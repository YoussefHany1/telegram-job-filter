"""
tests/test_engine.py

Unit tests for filters/engine.py (Section 28). No database, no Telegram -
pure string-in/result-out, exactly like the spec's four test cases ask for.
"""

from filters.engine import FilterEngine
from filters.rules import MatchMode

engine = FilterEngine()


# ---- Section 28's four canonical tests, verbatim -------------------------

def test_1_match_single_keyword():
    result = engine.evaluate("Looking for React Native Developer", ["React Native"], [], MatchMode.OR)
    assert result.matched


def test_2_no_match_unrelated_message():
    result = engine.evaluate("Looking for Python Developer", ["React Native"], [], MatchMode.OR)
    assert not result.matched


def test_3_exclude_keyword_blocks_match():
    result = engine.evaluate("Senior React Native Developer", ["React Native"], ["Senior"], MatchMode.OR)
    assert not result.matched
    assert result.reason == "excluded"


def test_4_case_insensitive_match():
    result = engine.evaluate("react native developer", ["React Native"], [], MatchMode.OR)
    assert result.matched


# ---- Extra coverage from the spec's other worked examples -----------------

def test_or_mode_matches_on_any_keyword():
    """Section 6 OR example."""
    result = engine.evaluate(
        "Flutter Developer Needed", ["React Native", "Flutter", "React"], [], MatchMode.OR
    )
    assert result.matched


def test_and_mode_requires_all_keywords():
    """Section 6 AND example - both present."""
    result = engine.evaluate(
        "React Native Developer\nExperience with Expo required",
        ["React Native", "Expo"],
        [],
        MatchMode.AND,
    )
    assert result.matched


def test_and_mode_fails_when_one_keyword_missing():
    """Section 6 AND example - only one present."""
    result = engine.evaluate("React Developer", ["React Native", "Expo"], [], MatchMode.AND)
    assert not result.matched


def test_include_exclude_forward_case():
    """Section 7 - passes include, no exclude hit -> forward."""
    result = engine.evaluate(
        "React Native Developer\nRemote\n2 years experience",
        ["React Native", "Expo", "Flutter", "Frontend"],
        ["Senior", "Manager", "Internship", "Unpaid"],
        MatchMode.OR,
    )
    assert result.matched


def test_include_exclude_ignore_case():
    """Section 7 - include matches but exclude keyword present -> ignore."""
    result = engine.evaluate(
        "Senior React Native Engineer",
        ["React Native", "Expo", "Flutter", "Frontend"],
        ["Senior", "Manager", "Internship", "Unpaid"],
        MatchMode.OR,
    )
    assert not result.matched


def test_arabic_mixed_text_match():
    """Section 9 Arabic/English mixed example."""
    result = engine.evaluate(
        "مطلوب مطور React Native للعمل عن بعد", ["مطور React"], [], MatchMode.OR
    )
    assert result.matched


def test_no_include_keywords_configured_never_matches():
    """No include keywords -> nothing to forward, not 'match everything'."""
    result = engine.evaluate("Anything at all here", [], [], MatchMode.OR)
    assert not result.matched


def test_long_message_is_handled():
    long_text = "React Native Developer needed. " + ("Details about the role. " * 200)
    result = engine.evaluate(long_text, ["React Native"], [], MatchMode.OR)
    assert result.matched

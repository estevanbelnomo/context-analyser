#!/usr/bin/env python3
"""
Unit tests for scripts/boundary_check.py.
No external test framework — plain Python runner.
"""

from __future__ import annotations

import sys
import traceback
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Import target module
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "context-analyser" / "scripts"))

import boundary_check as bc  # noqa: E402


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_PASS: list[str] = []
_FAIL: list[str] = []


def _run(name: str, fn) -> None:
    try:
        fn()
        _PASS.append(name)
        print(f"  PASS  {name}")
    except Exception as exc:
        _FAIL.append(name)
        print(f"  FAIL  {name}")
        traceback.print_exc()


def _assert(condition: bool, msg: str = "") -> None:
    if not condition:
        raise AssertionError(msg or "Assertion failed")


# ---------------------------------------------------------------------------
# 1. extract_keywords
# ---------------------------------------------------------------------------


def test_extract_keywords_filters_fillers():
    result = bc.extract_keywords("the quick brown fox is very fast")
    _assert("the" not in result, "'the' should be filtered")
    _assert("is" not in result, "'is' should be filtered")
    _assert("very" not in result, "'very' should be filtered")
    _assert("quick" in result, "'quick' should be kept")
    _assert("brown" in result, "'brown' should be kept")
    _assert("fox" in result, "'fox' should be kept")


def test_extract_keywords_empty_input():
    result = bc.extract_keywords("")
    _assert(result == Counter(), f"Expected empty Counter, got {result}")


def test_extract_keywords_single_char_filtered():
    result = bc.extract_keywords("a b c do go")
    # single-char words should be filtered (len > 1 required)
    for key in result:
        _assert(len(key) > 1, f"Single-char word '{key}' should have been filtered")


def test_extract_keywords_returns_counter():
    result = bc.extract_keywords("hello world hello")
    _assert(isinstance(result, Counter), "Should return a Counter")
    _assert(result["hello"] == 2, f"Expected hello=2, got {result['hello']}")


# ---------------------------------------------------------------------------
# 2. extract_negations
# ---------------------------------------------------------------------------


def test_extract_negations_multiple():
    text = "Never use eval. Do not import pickle."
    negations = bc.extract_negations(text)
    _assert(
        len(negations) >= 2,
        f"Expected >= 2 negations, got {len(negations)}: {negations}",
    )


def test_extract_negations_none():
    text = "Use parameterised queries always."
    negations = bc.extract_negations(text)
    _assert(
        len(negations) == 0,
        f"Expected 0 negations, got {len(negations)}: {negations}",
    )


def test_extract_negations_dont():
    text = "Don't use string interpolation."
    negations = bc.extract_negations(text)
    _assert(
        len(negations) >= 1,
        f"Expected >= 1 negation, got {len(negations)}: {negations}",
    )


# ---------------------------------------------------------------------------
# 3. classify_polarity
# ---------------------------------------------------------------------------


def test_classify_polarity_positive():
    text = "Always use parameterised queries. Must ensure safety."
    result = bc.classify_polarity(text)
    _assert(result == "positive", f"Expected 'positive', got '{result}'")


def test_classify_polarity_negative():
    text = "Never use eval. Avoid pickle. Don't import subprocess."
    result = bc.classify_polarity(text)
    _assert(result == "negative", f"Expected 'negative', got '{result}'")


def test_classify_polarity_neutral():
    text = "The sky is blue."
    result = bc.classify_polarity(text)
    _assert(result == "neutral", f"Expected 'neutral', got '{result}'")


# ---------------------------------------------------------------------------
# 4. check_semantic_preservation
# ---------------------------------------------------------------------------


def test_semantic_safe_compression():
    original = "You should always make sure to use parameterised queries when writing SQL."
    proposed = "Use parameterised SQL queries."
    result = bc.check_semantic_preservation(original, proposed)
    _assert(
        result["keyword_jaccard"] >= 0.55,
        f"Expected jaccard >= 0.55, got {result['keyword_jaccard']}",
    )
    _assert(result["passed"], f"Expected passed=True, issues: {result['issues']}")


def test_semantic_negation_dropped():
    original = "Never use eval() in production code."
    proposed = "Use eval() carefully in production code."
    result = bc.check_semantic_preservation(original, proposed)
    _assert(
        not result["negations_preserved"],
        f"Expected negations_preserved=False, got {result['negations_preserved']}",
    )
    _assert(not result["passed"], "Expected passed=False when negation dropped")


def test_semantic_polarity_flip():
    original = "Always use strict mode. Must enable linting."
    proposed = "Never use strict mode. Avoid linting."
    result = bc.check_semantic_preservation(original, proposed)
    _assert(
        not result["polarity_preserved"],
        f"Expected polarity_preserved=False, got {result['polarity_preserved']}",
    )
    _assert(not result["passed"], "Expected passed=False when polarity flipped")


def test_semantic_too_different():
    original = "Always use parameterised queries when writing SQL to prevent injection."
    proposed = "The weather today is sunny with a high of 75 degrees Fahrenheit."
    result = bc.check_semantic_preservation(original, proposed)
    _assert(
        result["keyword_jaccard"] < 0.55,
        f"Expected jaccard < 0.55, got {result['keyword_jaccard']}",
    )
    _assert(not result["passed"], "Expected passed=False for unrelated text")


def test_semantic_identical():
    text = "Always use parameterised queries."
    result = bc.check_semantic_preservation(text, text)
    _assert(
        result["keyword_jaccard"] == 1.0,
        f"Expected jaccard == 1.0 for identical text, got {result['keyword_jaccard']}",
    )
    _assert(result["passed"], "Expected passed=True for identical text")


# ---------------------------------------------------------------------------
# 5. is_instruction_file
# ---------------------------------------------------------------------------


def test_is_instruction_file_claude_md():
    result = bc.is_instruction_file(Path("CLAUDE.md"))
    _assert(result == "yes", f"Expected 'yes' for CLAUDE.md, got '{result}'")


def test_is_instruction_file_dotclaude():
    result = bc.is_instruction_file(Path(".claude/database.md"))
    _assert(result == "yes", f"Expected 'yes' for .claude/database.md, got '{result}'")


def test_is_instruction_file_docs_ambiguous():
    result = bc.is_instruction_file(Path("docs/checklist.md"))
    _assert(result == "ambiguous", f"Expected 'ambiguous' for docs/checklist.md, got '{result}'")


def test_is_instruction_file_source_no():
    result = bc.is_instruction_file(Path("src/main.rs"))
    _assert(result == "no", f"Expected 'no' for src/main.rs, got '{result}'")


def test_is_instruction_file_script_no():
    result = bc.is_instruction_file(Path("scripts/count_tokens.py"))
    _assert(result == "no", f"Expected 'no' for scripts/count_tokens.py, got '{result}'")


# ---------------------------------------------------------------------------
# 6. is_in_instruction_tree
# ---------------------------------------------------------------------------


def test_is_in_instruction_tree_claude_md():
    result = bc.is_in_instruction_tree(Path("CLAUDE.md"))
    _assert(result is True, f"Expected True for CLAUDE.md, got {result}")


def test_is_in_instruction_tree_dotclaude():
    result = bc.is_in_instruction_tree(Path(".claude/ui.md"))
    _assert(result is True, f"Expected True for .claude/ui.md, got {result}")


def test_is_in_instruction_tree_source():
    result = bc.is_in_instruction_tree(Path("src/main.rs"))
    _assert(result is False, f"Expected False for src/main.rs, got {result}")


# ---------------------------------------------------------------------------
# 7. preflight_check
# ---------------------------------------------------------------------------


def test_preflight_audit_readonly():
    """Audit CLAUDE.md (read-only) -> CLEAR, score 100."""
    result = bc.preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
        has_confirmation_gate=True,
        references_prior_session=False,
        involves_python_network=False,
    )
    _assert(result["classification"] == "CLEAR", f"Expected CLEAR, got {result['classification']}")
    _assert(result["score"] == 100, f"Expected score 100, got {result['score']}")


def test_preflight_compress_with_gate():
    """Compress CLAUDE.md with gate -> CLEAR, score >= 80."""
    result = bc.preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["CLAUDE.md"],
        action_type="compress",
        is_read_only=False,
        has_confirmation_gate=True,
        references_prior_session=False,
        involves_python_network=False,
    )
    _assert(result["classification"] == "CLEAR", f"Expected CLEAR, got {result['classification']}")
    _assert(result["score"] >= 80, f"Expected score >= 80, got {result['score']}")


def test_preflight_source_target_violation():
    """Source code target -> VIOLATION, score 0."""
    result = bc.preflight_check(
        target_files=["src/main.rs"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
        has_confirmation_gate=True,
    )
    _assert(result["classification"] == "VIOLATION", f"Expected VIOLATION, got {result['classification']}")
    _assert(result["score"] == 0, f"Expected score 0, got {result['score']}")


def test_preflight_no_confirmation_gate():
    """No confirmation gate for write -> VIOLATION."""
    result = bc.preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["CLAUDE.md"],
        action_type="compress",
        is_read_only=False,
        has_confirmation_gate=False,
    )
    _assert(result["classification"] == "VIOLATION", f"Expected VIOLATION, got {result['classification']}")
    _assert(result["score"] == 0, f"Expected score 0, got {result['score']}")


def test_preflight_add_instruction_violation():
    """add_instruction action -> VIOLATION."""
    result = bc.preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["CLAUDE.md"],
        action_type="add_instruction",
        is_read_only=False,
        has_confirmation_gate=True,
    )
    _assert(result["classification"] == "VIOLATION", f"Expected VIOLATION, got {result['classification']}")
    _assert(result["score"] == 0, f"Expected score 0, got {result['score']}")


def test_preflight_references_prior_session():
    """references_prior_session -> VIOLATION."""
    result = bc.preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
        has_confirmation_gate=True,
        references_prior_session=True,
    )
    _assert(result["classification"] == "VIOLATION", f"Expected VIOLATION, got {result['classification']}")
    _assert(result["score"] == 0, f"Expected score 0, got {result['score']}")


def test_preflight_involves_python_network():
    """involves_python_network -> VIOLATION."""
    result = bc.preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
        has_confirmation_gate=True,
        references_prior_session=False,
        involves_python_network=True,
    )
    _assert(result["classification"] == "VIOLATION", f"Expected VIOLATION, got {result['classification']}")
    _assert(result["score"] == 0, f"Expected score 0, got {result['score']}")


def test_preflight_ambiguous_docs_target():
    """Ambiguous docs/ write target -> AMBIGUOUS, score 50-79.
    A read-only audit of an ambiguous file scores 80 (CLEAR) because
    Boundary B gives full 20 pts. A write operation drops B to 15 and
    A to 10, producing a score in the AMBIGUOUS range."""
    result = bc.preflight_check(
        target_files=["docs/checklist.md"],
        write_targets=["docs/checklist.md"],
        action_type="compress",
        is_read_only=False,
        has_confirmation_gate=True,
        references_prior_session=False,
        involves_python_network=False,
    )
    _assert(result["classification"] == "AMBIGUOUS", f"Expected AMBIGUOUS, got {result['classification']}")
    _assert(
        50 <= result["score"] <= 79,
        f"Expected score 50-79, got {result['score']}",
    )


def test_preflight_write_outside_tree():
    """Write outside instruction tree -> VIOLATION."""
    result = bc.preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["src/main.rs"],
        action_type="compress",
        is_read_only=False,
        has_confirmation_gate=True,
        references_prior_session=False,
        involves_python_network=False,
    )
    _assert(result["classification"] == "VIOLATION", f"Expected VIOLATION, got {result['classification']}")
    _assert(result["score"] == 0, f"Expected score 0, got {result['score']}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_ALL_TESTS = [
    # extract_keywords
    ("extract_keywords: filters fillers", test_extract_keywords_filters_fillers),
    ("extract_keywords: empty input", test_extract_keywords_empty_input),
    ("extract_keywords: single-char filtered", test_extract_keywords_single_char_filtered),
    ("extract_keywords: returns Counter", test_extract_keywords_returns_counter),
    # extract_negations
    ("extract_negations: multiple", test_extract_negations_multiple),
    ("extract_negations: none", test_extract_negations_none),
    ("extract_negations: dont", test_extract_negations_dont),
    # classify_polarity
    ("classify_polarity: positive", test_classify_polarity_positive),
    ("classify_polarity: negative", test_classify_polarity_negative),
    ("classify_polarity: neutral", test_classify_polarity_neutral),
    # check_semantic_preservation
    ("check_semantic_preservation: safe compression", test_semantic_safe_compression),
    ("check_semantic_preservation: negation dropped", test_semantic_negation_dropped),
    ("check_semantic_preservation: polarity flip", test_semantic_polarity_flip),
    ("check_semantic_preservation: too different", test_semantic_too_different),
    ("check_semantic_preservation: identical", test_semantic_identical),
    # is_instruction_file
    ("is_instruction_file: CLAUDE.md -> yes", test_is_instruction_file_claude_md),
    ("is_instruction_file: .claude/database.md -> yes", test_is_instruction_file_dotclaude),
    ("is_instruction_file: docs/checklist.md -> ambiguous", test_is_instruction_file_docs_ambiguous),
    ("is_instruction_file: src/main.rs -> no", test_is_instruction_file_source_no),
    ("is_instruction_file: scripts/count_tokens.py -> no", test_is_instruction_file_script_no),
    # is_in_instruction_tree
    ("is_in_instruction_tree: CLAUDE.md -> True", test_is_in_instruction_tree_claude_md),
    ("is_in_instruction_tree: .claude/ui.md -> True", test_is_in_instruction_tree_dotclaude),
    ("is_in_instruction_tree: src/main.rs -> False", test_is_in_instruction_tree_source),
    # preflight_check
    ("preflight_check: audit read-only -> CLEAR 100", test_preflight_audit_readonly),
    ("preflight_check: compress with gate -> CLEAR >=80", test_preflight_compress_with_gate),
    ("preflight_check: source target -> VIOLATION 0", test_preflight_source_target_violation),
    ("preflight_check: no confirmation gate -> VIOLATION", test_preflight_no_confirmation_gate),
    ("preflight_check: add_instruction -> VIOLATION", test_preflight_add_instruction_violation),
    ("preflight_check: references_prior_session -> VIOLATION", test_preflight_references_prior_session),
    ("preflight_check: involves_python_network -> VIOLATION", test_preflight_involves_python_network),
    ("preflight_check: ambiguous docs target -> AMBIGUOUS 50-79", test_preflight_ambiguous_docs_target),
    ("preflight_check: write outside tree -> VIOLATION", test_preflight_write_outside_tree),
]

if __name__ == "__main__":
    print(f"\nRunning {len(_ALL_TESTS)} tests for boundary_check.py\n")
    for name, fn in _ALL_TESTS:
        _run(name, fn)

    total = len(_ALL_TESTS)
    passed = len(_PASS)
    failed = len(_FAIL)

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if _FAIL:
        print("\nFailed tests:")
        for name in _FAIL:
            print(f"  - {name}")
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)

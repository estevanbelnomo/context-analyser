#!/usr/bin/env python3
"""
Unit tests for scripts/count_tokens.py.
No external test framework — uses a simple pass/fail runner.
Run with: python tests/test_count_tokens.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "context-analyser" / "scripts"))

from count_tokens import (
    _pre_tokenize,
    _classify_line,
    count_tokens,
    _classify_zone,
    _boundary_warning,
    _parse_sections,
    _recommend_tier,
    audit_file,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_GREEN = str(FIXTURES / "sample_claude.md")
SAMPLE_BLOATED = str(FIXTURES / "sample_claude_bloated.md")

# ── helpers ─────────────────────────────────────────────────────────────────

_results: list[tuple[str, bool, str]] = []


def _assert(name: str, condition: bool, msg: str = "") -> None:
    _results.append((name, condition, msg))
    if not condition:
        detail = f" — {msg}" if msg else ""
        print(f"  FAIL  {name}{detail}")
    else:
        print(f"  pass  {name}")


# ── 1. _pre_tokenize ────────────────────────────────────────────────────────

def test_pre_tokenize() -> None:
    print("\n[1] _pre_tokenize")

    # Empty input
    result = _pre_tokenize("")
    _assert("empty string returns []", result == [], f"got {result!r}")

    # English words are split on whitespace boundaries
    words = _pre_tokenize("hello world")
    _assert(
        "simple words produce tokens",
        "hello" in words and "world" in words,
        f"got {words!r}",
    )

    # Contraction handled
    contractions = _pre_tokenize("don't")
    _assert(
        "contraction split correctly",
        "'t" in contractions or "don" in contractions,
        f"got {contractions!r}",
    )

    # Code-style token: underscores and identifiers
    code_tokens = _pre_tokenize("fn main() -> i32")
    _assert(
        "code tokens non-empty",
        len(code_tokens) > 0,
        f"got {code_tokens!r}",
    )

    # Numbers produce tokens
    num_tokens = _pre_tokenize("42 items")
    _assert(
        "numbers produce tokens",
        "42" in num_tokens,
        f"got {num_tokens!r}",
    )

    # Punctuation produces tokens
    punct = _pre_tokenize("a, b.")
    _assert(
        "punctuation produces tokens",
        len(punct) >= 4,
        f"got {punct!r}",
    )


# ── 2. _classify_line ───────────────────────────────────────────────────────

def test_classify_line() -> None:
    print("\n[2] _classify_line")

    # Whitespace
    _assert("blank line is whitespace", _classify_line("") == "whitespace")
    _assert("spaces-only is whitespace", _classify_line("   ") == "whitespace")

    # Prose
    _assert(
        "plain sentence is prose",
        _classify_line("This is a plain English sentence.") == "prose",
    )

    # Code signals — import
    _assert(
        "import line is code",
        _classify_line("import os") == "code",
    )

    # Code signals — fn
    _assert(
        "fn keyword is code",
        _classify_line("fn main() -> i32 {") == "code",
    )

    # Code signals — bullet point
    _assert(
        "bullet point (-) is code",
        _classify_line("- some rule") == "code",
    )

    # Code signals — asterisk bullet
    _assert(
        "bullet point (*) is code",
        _classify_line("* another rule") == "code",
    )

    # Path — .md reference
    _assert(
        ".md extension is path",
        _classify_line("See README.md for details") == "path",
    )

    # Path — .claude/ style
    _assert(
        ".claude/ path is path",
        _classify_line("load .claude/database.md") == "path",
    )

    # Path — unix style
    _assert(
        "unix multi-segment path is path",
        _classify_line("See /usr/local/bin for the binary") == "path",
    )


# ── 3. count_tokens ─────────────────────────────────────────────────────────

def test_count_tokens() -> None:
    print("\n[3] count_tokens")

    # Empty returns 0
    tok, method, accuracy = count_tokens("")
    _assert("empty text returns 0 tokens", tok == 0, f"got {tok}")
    _assert("method string is non-empty", bool(method))

    # Whitespace-only returns 0
    tok2, _, _ = count_tokens("   \n  ")
    _assert("whitespace-only returns 0", tok2 == 0, f"got {tok2}")

    # Short prose returns reasonable range
    sentence = "The quick brown fox jumps over the lazy dog."
    tok3, _, _ = count_tokens(sentence)
    _assert(
        "short prose returns 5-20 tokens",
        5 <= tok3 <= 20,
        f"got {tok3} for {sentence!r}",
    )

    # Always returns >= 1 for non-empty, non-whitespace text
    tok4, _, _ = count_tokens("x")
    _assert("single character returns >= 1", tok4 >= 1, f"got {tok4}")


# ── 4. _classify_zone ───────────────────────────────────────────────────────

def test_classify_zone() -> None:
    print("\n[4] _classify_zone")

    cases = [
        (0, "GREEN"),
        (499, "GREEN"),
        (500, "YELLOW"),
        (1999, "YELLOW"),
        (2000, "ORANGE"),
        (4999, "ORANGE"),
        (5000, "RED"),
        (9999, "RED"),
        (10000, "CRITICAL"),
    ]
    for tokens, expected in cases:
        zone, _ = _classify_zone(tokens)
        _assert(
            f"_classify_zone({tokens}) == {expected}",
            zone == expected,
            f"got {zone!r}",
        )


# ── 5. _boundary_warning ────────────────────────────────────────────────────

def test_boundary_warning() -> None:
    print("\n[5] _boundary_warning")

    # Safely in the middle of GREEN — no warning
    result = _boundary_warning(300)
    _assert(
        "_boundary_warning(300) returns None",
        result is None,
        f"got {result!r}",
    )

    # Near GREEN/YELLOW boundary (500): 490 * 1.06 = 519 -> crosses into YELLOW
    result2 = _boundary_warning(490)
    _assert(
        "_boundary_warning(490) returns a warning dict",
        result2 is not None,
        "expected warning near GREEN/YELLOW boundary",
    )
    if result2 is not None:
        _assert(
            "_boundary_warning(490) warning has 'possible_zones'",
            "possible_zones" in result2,
            f"keys: {list(result2.keys())}",
        )

    # Near YELLOW/ORANGE boundary (2000): 1950 * 1.06 = 2067 -> crosses into ORANGE
    result3 = _boundary_warning(1950)
    _assert(
        "_boundary_warning(1950) returns a warning dict",
        result3 is not None,
        "expected warning near YELLOW/ORANGE boundary",
    )


# ── 6. _parse_sections ──────────────────────────────────────────────────────

def test_parse_sections() -> None:
    print("\n[6] _parse_sections")

    # Basic header splitting
    content = "preamble text\n\n# Section A\nbody A\n\n# Section B\nbody B"
    sections = _parse_sections(content)
    headers = [s["header"] for s in sections]
    _assert(
        "preamble section present",
        "(preamble)" in headers,
        f"headers: {headers}",
    )
    _assert(
        "Section A present",
        "Section A" in headers,
        f"headers: {headers}",
    )
    _assert(
        "Section B present",
        "Section B" in headers,
        f"headers: {headers}",
    )
    _assert(
        "basic split produces 3 sections",
        len(sections) == 3,
        f"got {len(sections)}",
    )

    # Nested headers with levels
    nested = "# Top\n## Sub\nbody\n### Deep\ndeep body"
    nsecs = _parse_sections(nested)
    levels = {s["header"]: s["level"] for s in nsecs}
    _assert(
        "level 1 header has level 1",
        levels.get("Top") == 1,
        f"levels: {levels}",
    )
    _assert(
        "level 2 header has level 2",
        levels.get("Sub") == 2,
        f"levels: {levels}",
    )
    _assert(
        "level 3 header has level 3",
        levels.get("Deep") == 3,
        f"levels: {levels}",
    )

    # Preamble-only content (no headers)
    preamble_only = "just some text\nno headers here"
    psecs = _parse_sections(preamble_only)
    _assert(
        "preamble-only produces exactly 1 section",
        len(psecs) == 1,
        f"got {len(psecs)}",
    )
    _assert(
        "preamble-only section header is (preamble)",
        psecs[0]["header"] == "(preamble)",
        f"got {psecs[0]['header']!r}",
    )


# ── 7. _recommend_tier ──────────────────────────────────────────────────────

def test_recommend_tier() -> None:
    print("\n[7] _recommend_tier")

    # Core section signal ("Rules"), small size -> T0
    tier, reason = _recommend_tier("Rules", 150, 10.0)
    _assert(
        "Rules section 150tok -> T0",
        tier == 0,
        f"got tier={tier}, reason={reason!r}",
    )

    # Large section -> T2
    tier2, reason2 = _recommend_tier("Database Conventions", 900, 30.0)
    _assert(
        "large section 900tok -> T2",
        tier2 == 2,
        f"got tier={tier2}, reason={reason2!r}",
    )

    # Domain section: 400tok not core -> T1
    tier3, reason3 = _recommend_tier("Export Format Specification", 400, 15.0)
    _assert(
        "domain section 400tok -> T1",
        tier3 == 1,
        f"got tier={tier3}, reason={reason3!r}",
    )

    # Small section: 50tok, 3% pct -> T0 (small enough to remain)
    tier4, reason4 = _recommend_tier("Misc Notes", 50, 3.0)
    _assert(
        "small section 50tok 3pct -> T0",
        tier4 == 0,
        f"got tier={tier4}, reason={reason4!r}",
    )


# ── 8. audit_file ───────────────────────────────────────────────────────────

def test_audit_file() -> None:
    print("\n[8] audit_file")

    # GREEN fixture
    green = audit_file(SAMPLE_GREEN)

    _assert(
        "GREEN fixture: total_tokens > 0",
        green["total_tokens"] > 0,
        f"got {green['total_tokens']}",
    )
    _assert(
        "GREEN fixture: total_zone is GREEN or YELLOW",
        green["total_zone"] in ("GREEN", "YELLOW"),
        f"got {green['total_zone']}",
    )
    _assert(
        "GREEN fixture: sections list is non-empty",
        len(green["sections"]) > 0,
        f"got {len(green['sections'])} sections",
    )
    _assert(
        "GREEN fixture: sections sorted descending by tokens",
        all(
            green["sections"][i]["tokens"] >= green["sections"][i + 1]["tokens"]
            for i in range(len(green["sections"]) - 1)
        ),
        "sections not in descending order",
    )

    # Bloated fixture — YELLOW+ zone
    bloated = audit_file(SAMPLE_BLOATED)

    _assert(
        "BLOATED fixture: total_tokens > 500",
        bloated["total_tokens"] > 500,
        f"got {bloated['total_tokens']}",
    )
    _assert(
        "BLOATED fixture: total_zone is YELLOW, ORANGE, or RED",
        bloated["total_zone"] in ("YELLOW", "ORANGE", "RED"),
        f"got {bloated['total_zone']}",
    )
    _assert(
        "BLOATED fixture: sections non-empty",
        len(bloated["sections"]) > 0,
        f"got {len(bloated['sections'])} sections",
    )
    _assert(
        "BLOATED fixture: positive estimated_reduction_pct or zero",
        bloated["estimated_reduction_pct"] >= 0,
        f"got {bloated['estimated_reduction_pct']}",
    )
    _assert(
        "BLOATED fixture: sections sorted descending by tokens",
        all(
            bloated["sections"][i]["tokens"] >= bloated["sections"][i + 1]["tokens"]
            for i in range(len(bloated["sections"]) - 1)
        ),
        "sections not in descending order",
    )

    # Invalid path raises ValueError
    raised = False
    try:
        audit_file("/nonexistent/path/that/does/not/exist.md")
    except ValueError:
        raised = True
    _assert(
        "invalid path raises ValueError",
        raised,
        "no exception raised",
    )


# ── Runner ───────────────────────────────────────────────────────────────────

def main() -> None:
    test_fns = [
        test_pre_tokenize,
        test_classify_line,
        test_count_tokens,
        test_classify_zone,
        test_boundary_warning,
        test_parse_sections,
        test_recommend_tier,
        test_audit_file,
    ]

    for fn in test_fns:
        try:
            fn()
        except Exception:
            print(f"\n  EXCEPTION in {fn.__name__}:")
            traceback.print_exc()
            _results.append((fn.__name__, False, "uncaught exception"))

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    total = len(_results)

    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

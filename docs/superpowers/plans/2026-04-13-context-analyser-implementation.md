# Context Analyser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden, test, and validate the context-analyser skill so all 8 success criteria pass.

**Architecture:** Skill Family (Approach 2). Lean SKILL.md (<500 tok) + JIT reference files. Python scripts (stdlib only) for token counting and boundary enforcement. Bash script for exact API-based counts. All files already scaffolded — this plan covers testing, bug fixes, and validation.

**Tech Stack:** Python 3.10+ (stdlib only), Bash, Anthropic count_tokens API, Claude Code skill system.

**Working Directory:** `P:\Work\Programming\_Claude_Skills\context-analyser`

**Spec:** `docs/superpowers/specs/2026-04-13-context-analyser-design.md`

---

## File Map

All files already exist. This plan modifies them as needed and adds a test file.

| File | Status | This Plan |
|------|--------|-----------|
| `SKILL.md` | Exists, 494 tok body | Validate only |
| `scripts/count_tokens.sh` | Exists | Test + fix bugs |
| `scripts/count_tokens.py` | Exists, 491 lines | Test + fix bugs |
| `scripts/boundary_check.py` | Exists, 397 lines | Test + fix bugs |
| `scripts/self_test.py` | Exists, 249 lines | Already passing |
| `references/*.md` (6 files) | Exist, within budget | Validate only |
| `tests/test_count_tokens.py` | **Create** | Unit tests for token counter |
| `tests/test_boundary_check.py` | **Create** | Unit tests for boundary checker |
| `tests/fixtures/sample_claude.md` | **Create** | Test fixture: known CLAUDE.md |
| `tests/fixtures/sample_claude_bloated.md` | **Create** | Test fixture: ORANGE-zone file |

---

### Task 1: Create Test Fixtures

**Files:**
- Create: `tests/fixtures/sample_claude.md`
- Create: `tests/fixtures/sample_claude_bloated.md`

- [ ] **Step 1: Create tests directory**

Run: `mkdir -p tests/fixtures`

- [ ] **Step 2: Create GREEN-zone test fixture (~300 tokens)**

Create `tests/fixtures/sample_claude.md`:

```markdown
# TestProject
Rust/Tauri v2. Desktop stock query tool.

## Rules
- Parameterised SQL only. No string interpolation.
- Use thiserror (lib) / anyhow (bin). No unwrap() in production.
- All public functions require tests.
- British English in user-facing strings.

## Context Loading
When working on database/SQL, load .claude/database.md
When working on UI/components, load .claude/ui.md

## Commands
/audit    Analyse CLAUDE.md token usage
/schema   Load current database ERD

## Session Management
- After completing a task, summarise outcome in 1-2 lines.
- Do not retain file contents in context. Reference by path.
```

- [ ] **Step 3: Create ORANGE-zone test fixture (~2500 tokens)**

Create `tests/fixtures/sample_claude_bloated.md`:

```markdown
# TestProject: SimPRO Database Tool
Rust/Tauri v2/Leptos/PostgreSQL. Desktop application for stock management queries and exports.

## Universal Rules
- You should always make sure to use parameterised queries when writing SQL. Never use string interpolation for SQL queries as this could lead to SQL injection vulnerabilities.
- It is important that you use thiserror for library code and anyhow for binary code. Please note that you should never use unwrap() in production code. Instead, use the ? operator or provide explicit error handling with meaningful error messages.
- All public functions require comprehensive test coverage. Tests should cover both the happy path and error cases.
- Please use British English in all user-facing strings and documentation.
- When writing commit messages, always follow the conventional commits format: type(scope): description.

## Database Conventions
- Always create reversible migrations with both up and down scripts.
- Migration file naming format should be YYYYMMDD_HHMMSS_description.sql.
- Before generating any migration SQL, you should read the migration checklist at docs/migration-checklist.md.
- Test all migrations against a throwaway database before applying them to the development database.
- Use Common Table Expressions (CTEs) for complex queries. Do not use nested subqueries beyond 2 levels of nesting.
- All JOIN operations must specify the join type explicitly (INNER JOIN, LEFT JOIN, etc.). Never use implicit joins.
- You should create an index for any column that is used in a WHERE clause or JOIN condition if the table has more than 10,000 rows.
- Primary keys should always be id BIGSERIAL.
- All tables must have created_at TIMESTAMPTZ DEFAULT now() and updated_at TIMESTAMPTZ columns.
- For soft deletes, use deleted_at TIMESTAMPTZ NULL.
- All foreign keys must specify ON DELETE behaviour (CASCADE, SET NULL, RESTRICT, etc.).

## UI Component Patterns
- All Leptos components should follow the signal-based reactivity pattern.
- Use the component macro (#[component]) for all public components.
- Props must implement Clone and PartialEq for memoisation.
- Style with Tailwind utility classes. No custom CSS unless absolutely necessary.
- All user-facing text must go through the i18n system.
- Error states should always show a user-friendly message, not raw error text.
- Loading states are required for any async operation.

## Export Format Specification
- The primary export format is XLSX for Xero integration.
- Column headers must match the Xero import template exactly. See docs/xero-export-spec.md for the full mapping.
- Date format in exports: YYYY-MM-DD (ISO 8601).
- Currency values must be formatted with 2 decimal places, no currency symbol.
- The export should include a summary row at the bottom with totals for all numeric columns.
- Maximum export size is 50,000 rows. For larger datasets, split into multiple files.

## Testing Rules
- Use the test fixtures in tests/fixtures/ directory. Do not create ad-hoc test data.
- Integration tests must use a real PostgreSQL database, not mocks.
- Test database is automatically provisioned by the test harness.
- Snapshot tests for all UI components.
- Performance tests required for any query touching tables with more than 100K rows.

## Deployment
- Tauri builds must be signed with the project signing key.
- CI pipeline runs on every push to main.
- Release builds use the release profile with optimisations enabled.
- The application auto-updates via Tauri's built-in updater.
- Environment-specific configuration goes in config/{env}.toml.

## Context Management
- After completing a task, summarise the outcome in 1-2 lines and discard intermediate reasoning.
- Do not keep file contents in context after processing. Reference files by path only.
- When conversation exceeds 50 messages, create a PROGRESS.md with current state before continuing.
- When reading reference files, extract only what is needed for the current task.
```

- [ ] **Step 4: Commit fixtures**

```bash
git add tests/fixtures/sample_claude.md tests/fixtures/sample_claude_bloated.md
git commit -m "test: add CLAUDE.md fixtures for GREEN and ORANGE zones"
```

---

### Task 2: Test count_tokens.py Core Functions

**Files:**
- Create: `tests/test_count_tokens.py`
- Read: `scripts/count_tokens.py`

- [ ] **Step 1: Write failing tests for count_tokens core**

Create `tests/test_count_tokens.py`:

```python
#!/usr/bin/env python3
"""Tests for count_tokens.py core functions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from count_tokens import (
    _classify_line,
    _classify_zone,
    _boundary_warning,
    _parse_sections,
    _pre_tokenize,
    _recommend_tier,
    audit_file,
    count_tokens,
)


def test_pre_tokenize_english_words():
    tokens = _pre_tokenize("Hello world")
    assert "Hello" in tokens
    assert "world" in tokens


def test_pre_tokenize_code():
    tokens = _pre_tokenize("fn main() -> Result<T, Error> {")
    assert "fn" in tokens
    assert "main" in tokens


def test_pre_tokenize_empty():
    assert _pre_tokenize("") == []


def test_classify_line_prose():
    assert _classify_line("Use parameterised SQL only.") == "prose"


def test_classify_line_code():
    assert _classify_line("import json") == "code"
    assert _classify_line("fn main() {") == "code"
    assert _classify_line("- bullet point") == "code"


def test_classify_line_path():
    assert _classify_line("See docs/migration-checklist.md") == "path"
    assert _classify_line("Load .claude/database.md") == "path"


def test_classify_line_whitespace():
    assert _classify_line("") == "whitespace"
    assert _classify_line("   ") == "whitespace"


def test_count_tokens_empty():
    tokens, method, acc = count_tokens("")
    assert tokens == 0
    assert method == "regex_pretokenizer"


def test_count_tokens_short_prose():
    tokens, _, _ = count_tokens("Hello world, this is a test.")
    assert 5 <= tokens <= 15


def test_count_tokens_returns_positive():
    tokens, _, _ = count_tokens("x")
    assert tokens >= 1


def test_classify_zone_green():
    zone, action = _classify_zone(300)
    assert zone == "GREEN"


def test_classify_zone_yellow():
    zone, _ = _classify_zone(1000)
    assert zone == "YELLOW"


def test_classify_zone_orange():
    zone, _ = _classify_zone(3000)
    assert zone == "ORANGE"


def test_classify_zone_red():
    zone, _ = _classify_zone(7000)
    assert zone == "RED"


def test_classify_zone_critical():
    zone, _ = _classify_zone(15000)
    assert zone == "CRITICAL"


def test_classify_zone_boundaries():
    assert _classify_zone(0)[0] == "GREEN"
    assert _classify_zone(499)[0] == "GREEN"
    assert _classify_zone(500)[0] == "YELLOW"
    assert _classify_zone(1999)[0] == "YELLOW"
    assert _classify_zone(2000)[0] == "ORANGE"
    assert _classify_zone(4999)[0] == "ORANGE"
    assert _classify_zone(5000)[0] == "RED"
    assert _classify_zone(9999)[0] == "RED"
    assert _classify_zone(10000)[0] == "CRITICAL"


def test_boundary_warning_clear():
    # 300 tokens is well inside GREEN (0-500), no boundary warning
    warning = _boundary_warning(300)
    assert warning is None


def test_boundary_warning_near_green_yellow():
    # 490 tokens: +6% = 519 (YELLOW), so should warn
    warning = _boundary_warning(490)
    assert warning is not None
    assert "GREEN" in warning["possible_zones"]
    assert "YELLOW" in warning["possible_zones"]


def test_boundary_warning_near_yellow_orange():
    warning = _boundary_warning(1950)
    assert warning is not None


def test_parse_sections_basic():
    content = "# Header 1\nBody 1\n# Header 2\nBody 2"
    sections = _parse_sections(content)
    assert len(sections) == 3  # preamble + 2 headers
    assert sections[0]["header"] == "(preamble)"
    assert sections[1]["header"] == "Header 1"
    assert sections[2]["header"] == "Header 2"


def test_parse_sections_nested():
    content = "# H1\nText\n## H2\nMore text"
    sections = _parse_sections(content)
    assert sections[1]["level"] == 1
    assert sections[2]["level"] == 2


def test_parse_sections_preamble_only():
    content = "No headers here\nJust text"
    sections = _parse_sections(content)
    assert len(sections) == 1
    assert sections[0]["header"] == "(preamble)"


def test_recommend_tier_core_section():
    tier, reason = _recommend_tier("Rules", 150, 20.0)
    assert tier == 0


def test_recommend_tier_large_section():
    tier, reason = _recommend_tier("Database Conventions", 900, 40.0)
    assert tier == 2


def test_recommend_tier_domain_section():
    tier, reason = _recommend_tier("Export Format", 400, 15.0)
    assert tier == 1


def test_recommend_tier_small_section():
    tier, reason = _recommend_tier("Misc", 50, 3.0)
    assert tier == 0


def test_audit_file_green_fixture():
    fixture = str(Path(__file__).parent / "fixtures" / "sample_claude.md")
    result = audit_file(fixture)
    assert result["total_zone"] in ("GREEN", "YELLOW")
    assert result["total_tokens"] > 0
    assert len(result["sections"]) > 0
    assert len(result["tier_suggestions"]) > 0
    assert "method" in result
    assert "accuracy" in result


def test_audit_file_bloated_fixture():
    fixture = str(Path(__file__).parent / "fixtures" / "sample_claude_bloated.md")
    result = audit_file(fixture)
    assert result["total_zone"] in ("YELLOW", "ORANGE", "RED")
    assert result["total_tokens"] > 500
    assert result["estimated_reduction_pct"] > 0


def test_audit_file_sections_sorted_descending():
    fixture = str(Path(__file__).parent / "fixtures" / "sample_claude_bloated.md")
    result = audit_file(fixture)
    tokens = [s["tokens"] for s in result["sections"]]
    assert tokens == sorted(tokens, reverse=True)


def test_audit_file_invalid_path():
    try:
        audit_file("/nonexistent/CLAUDE.md")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS  {test_fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL  {test_fn.__name__}")
            traceback.print_exc()
            print()

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run tests to see which fail**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python tests/test_count_tokens.py`

Expected: Some tests may fail if fixtures don't exist yet (Task 1 must complete first). All core function tests should pass.

- [ ] **Step 3: Fix any failing tests or bugs found**

Read the failure output. If a test exposes a bug in count_tokens.py, fix the bug in the script. If the test expectation is wrong, fix the test.

- [ ] **Step 4: Re-run and verify all pass**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python tests/test_count_tokens.py`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_count_tokens.py
git commit -m "test: add unit tests for count_tokens.py"
```

---

### Task 3: Test boundary_check.py

**Files:**
- Create: `tests/test_boundary_check.py`
- Read: `scripts/boundary_check.py`

- [ ] **Step 1: Write failing tests for boundary checker**

Create `tests/test_boundary_check.py`:

```python
#!/usr/bin/env python3
"""Tests for boundary_check.py functions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from boundary_check import (
    check_semantic_preservation,
    classify_polarity,
    extract_keywords,
    extract_negations,
    is_in_instruction_tree,
    is_instruction_file,
    preflight_check,
)


# == Keyword Extraction ==

def test_extract_keywords_filters_filler():
    kw = extract_keywords("the quick brown fox is very fast")
    assert "quick" in kw
    assert "brown" in kw
    assert "fox" in kw
    assert "fast" in kw
    assert "the" not in kw
    assert "is" not in kw
    assert "very" not in kw


def test_extract_keywords_empty():
    kw = extract_keywords("")
    assert len(kw) == 0


def test_extract_keywords_single_char_filtered():
    kw = extract_keywords("a b c x y z")
    assert len(kw) == 0


# == Negation Detection ==

def test_extract_negations_basic():
    negs = extract_negations("Never use eval. Do not import pickle.")
    assert len(negs) >= 2


def test_extract_negations_none():
    negs = extract_negations("Use parameterised queries always.")
    assert len(negs) == 0


def test_extract_negations_contraction():
    negs = extract_negations("Don't use string interpolation.")
    assert len(negs) >= 1


# == Polarity ==

def test_polarity_positive():
    assert classify_polarity("Always use parameterised queries. Must ensure safety.") == "positive"


def test_polarity_negative():
    assert classify_polarity("Never use eval. Avoid pickle. Don't import subprocess.") == "negative"


def test_polarity_neutral():
    assert classify_polarity("The sky is blue.") == "neutral"


# == Semantic Preservation ==

def test_semantic_safe_compression():
    original = "You should always make sure to use parameterised queries when writing SQL."
    proposed = "Use parameterised SQL queries."
    result = check_semantic_preservation(original, proposed)
    assert result["passed"] is True
    assert result["keyword_jaccard"] >= 0.55


def test_semantic_negation_dropped():
    original = "Never use eval() in production code."
    proposed = "Use eval() carefully in production code."
    result = check_semantic_preservation(original, proposed)
    assert result["negations_preserved"] is False


def test_semantic_polarity_flip():
    original = "Always use strict mode. Must enable linting."
    proposed = "Never use strict mode. Avoid linting."
    result = check_semantic_preservation(original, proposed)
    assert result["polarity_preserved"] is False


def test_semantic_too_different():
    original = "Use parameterised queries for all database access."
    proposed = "The weather is nice today and birds are singing."
    result = check_semantic_preservation(original, proposed)
    assert result["passed"] is False
    assert result["keyword_jaccard"] < 0.55


def test_semantic_identical():
    text = "No unwrap() in production code."
    result = check_semantic_preservation(text, text)
    assert result["passed"] is True
    assert result["keyword_jaccard"] == 1.0


# == Scope Containment ==

def test_scope_claude_md():
    assert is_instruction_file(Path("CLAUDE.md")) == "yes"


def test_scope_claude_dir():
    assert is_instruction_file(Path(".claude/database.md")) == "yes"


def test_scope_docs_ambiguous():
    assert is_instruction_file(Path("docs/checklist.md")) == "ambiguous"


def test_scope_source_code():
    assert is_instruction_file(Path("src/main.rs")) == "no"


def test_scope_python_file():
    assert is_instruction_file(Path("scripts/count_tokens.py")) == "no"


# == File Tree Containment ==

def test_tree_claude_md():
    assert is_in_instruction_tree(Path("CLAUDE.md")) is True


def test_tree_claude_dir():
    assert is_in_instruction_tree(Path(".claude/ui.md")) is True


def test_tree_source():
    assert is_in_instruction_tree(Path("src/main.rs")) is False


# == Preflight Check ==

def test_preflight_audit_clear():
    result = preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
    )
    assert result["classification"] == "CLEAR"
    assert result["score"] == 100


def test_preflight_compress_clear():
    result = preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["CLAUDE.md"],
        action_type="compress",
        has_confirmation_gate=True,
    )
    assert result["classification"] == "CLEAR"
    assert result["score"] >= 80


def test_preflight_source_violation():
    result = preflight_check(
        target_files=["src/main.rs"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
    )
    assert result["classification"] == "VIOLATION"
    assert result["score"] == 0


def test_preflight_no_gate_violation():
    result = preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["CLAUDE.md"],
        action_type="compress",
        has_confirmation_gate=False,
    )
    assert result["classification"] == "VIOLATION"


def test_preflight_add_instruction_violation():
    result = preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["CLAUDE.md"],
        action_type="add_instruction",
        has_confirmation_gate=True,
    )
    assert result["classification"] == "VIOLATION"


def test_preflight_prior_session_violation():
    result = preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
        references_prior_session=True,
    )
    assert result["classification"] == "VIOLATION"


def test_preflight_python_network_violation():
    result = preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=[],
        action_type="audit",
        is_read_only=True,
        involves_python_network=True,
    )
    assert result["classification"] == "VIOLATION"


def test_preflight_ambiguous_docs():
    result = preflight_check(
        target_files=["docs/checklist.md"],
        write_targets=["docs/checklist.md"],
        action_type="compress",
        has_confirmation_gate=True,
    )
    assert result["classification"] == "AMBIGUOUS"
    assert 50 <= result["score"] < 80


def test_preflight_write_outside_tree():
    result = preflight_check(
        target_files=["CLAUDE.md"],
        write_targets=["src/main.rs"],
        action_type="compress",
        has_confirmation_gate=True,
    )
    assert result["classification"] == "VIOLATION"


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS  {test_fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL  {test_fn.__name__}")
            traceback.print_exc()
            print()

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run tests**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python tests/test_boundary_check.py`

Expected: Some tests may fail, revealing bugs in boundary_check.py.

- [ ] **Step 3: Fix any bugs found**

Common issues to watch for:
- `is_instruction_file` uses `path.resolve()` which may produce absolute paths that don't contain ".claude" as a substring on all platforms.
- `extract_negations` may miss edge cases with contractions.
- Polarity classification may produce unexpected results on mixed-polarity text.

Fix bugs in `scripts/boundary_check.py`. Do NOT change the test expectations unless the test is genuinely wrong per the spec.

- [ ] **Step 4: Re-run and verify all pass**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python tests/test_boundary_check.py`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_boundary_check.py
git commit -m "test: add unit tests for boundary_check.py"
```

---

### Task 4: Test count_tokens.sh (Bash Script)

**Files:**
- Read: `scripts/count_tokens.sh`
- Create: `tests/test_count_tokens_sh.sh`

- [ ] **Step 1: Write bash test script**

Create `tests/test_count_tokens_sh.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Tests for count_tokens.sh
# Requires: ANTHROPIC_API_KEY, curl, jq

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
COUNTER="$ROOT_DIR/scripts/count_tokens.sh"
FIXTURE="$ROOT_DIR/tests/fixtures/sample_claude.md"

passed=0
failed=0

fail() { echo "  FAIL  $1: $2"; ((failed++)); }
pass() { echo "  PASS  $1"; ((passed++)); }

# -- Test: Missing API key --
test_missing_api_key() {
    local name="missing_api_key"
    local out
    if out=$(ANTHROPIC_API_KEY="" bash "$COUNTER" "$FIXTURE" 2>&1); then
        fail "$name" "Expected non-zero exit"
    else
        if echo "$out" | grep -q "ANTHROPIC_API_KEY"; then
            pass "$name"
        else
            fail "$name" "Expected API key error message, got: $out"
        fi
    fi
}

# -- Test: Missing file --
test_missing_file() {
    local name="missing_file"
    local out
    if out=$(bash "$COUNTER" "/nonexistent/file.md" 2>&1); then
        fail "$name" "Expected non-zero exit"
    else
        if echo "$out" | grep -q "File not found"; then
            pass "$name"
        else
            fail "$name" "Expected file not found error, got: $out"
        fi
    fi
}

# -- Test: Valid file (requires API key) --
test_valid_file() {
    local name="valid_file"
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        echo "  SKIP  $name (ANTHROPIC_API_KEY not set)"
        return
    fi
    local out
    if out=$(bash "$COUNTER" "$FIXTURE" 2>/dev/null); then
        local total
        total=$(echo "$out" | jq '.total_tokens')
        if [[ "$total" -gt 0 ]]; then
            pass "$name (total=$total)"
        else
            fail "$name" "Expected positive token count, got: $total"
        fi
    else
        fail "$name" "Script exited with error"
    fi
}

# -- Test: Output JSON schema --
test_json_schema() {
    local name="json_schema"
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        echo "  SKIP  $name (ANTHROPIC_API_KEY not set)"
        return
    fi
    local out
    if out=$(bash "$COUNTER" "$FIXTURE" 2>/dev/null); then
        local has_fields
        has_fields=$(echo "$out" | jq 'has("file") and has("total_tokens") and has("zone") and has("method") and has("sections")')
        if [[ "$has_fields" == "true" ]]; then
            pass "$name"
        else
            fail "$name" "Missing required JSON fields"
        fi
    else
        fail "$name" "Script exited with error"
    fi
}

# -- Test: Python and bash agree within 6% --
test_python_bash_agreement() {
    local name="python_bash_agreement"
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        echo "  SKIP  $name (ANTHROPIC_API_KEY not set)"
        return
    fi
    local bash_total py_total
    bash_total=$(bash "$COUNTER" "$FIXTURE" 2>/dev/null | jq '.total_tokens')
    py_total=$(python "$ROOT_DIR/scripts/count_tokens.py" "$FIXTURE" --json 2>/dev/null | jq '.total_tokens')

    local diff pct
    diff=$(( bash_total > py_total ? bash_total - py_total : py_total - bash_total ))
    pct=$(python -c "print(round($diff / $bash_total * 100, 1))")

    if python -c "exit(0 if $diff / $bash_total < 0.06 else 1)"; then
        pass "$name (bash=$bash_total, py=$py_total, diff=${pct}%)"
    else
        fail "$name" "Difference ${pct}% exceeds 6% threshold (bash=$bash_total, py=$py_total)"
    fi
}

echo "========================================"
echo "  count_tokens.sh tests"
echo "========================================"

test_missing_api_key
test_missing_file
test_valid_file
test_json_schema
test_python_bash_agreement

echo ""
echo "----------------------------------------"
echo "  $passed passed, $failed failed"
echo "========================================"

exit $((failed > 0 ? 1 : 0))
```

- [ ] **Step 2: Make executable and run**

Run: `chmod +x tests/test_count_tokens_sh.sh && cd P:/Work/Programming/_Claude_Skills/context-analyser && bash tests/test_count_tokens_sh.sh`

Expected: `missing_api_key` and `missing_file` pass. API-dependent tests either pass (if key set) or skip.

- [ ] **Step 3: Fix any bugs found in count_tokens.sh**

- [ ] **Step 4: Commit**

```bash
git add tests/test_count_tokens_sh.sh
git commit -m "test: add bash tests for count_tokens.sh"
```

---

### Task 5: Run Security Verification Suite

**Files:**
- Read: `scripts/self_test.py`

- [ ] **Step 1: Run AST security scan**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/self_test.py`

Expected: `ALL FILES PASS SECURITY SCAN`

- [ ] **Step 2: Manual import audit**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && grep -rn "^import\|^from" scripts/*.py`

Verify: every import is in the permitted list (`__future__`, `ast`, `json`, `re`, `sys`, `collections`, `pathlib`).

- [ ] **Step 3: Network isolation verify**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && grep -rn "socket\|urllib\|http\.\|requests\|httpx" scripts/*.py`

Expected: zero matches.

- [ ] **Step 4: Dangerous builtin verify**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && grep -rn "eval(\|exec(\|__import__(\|pickle\|marshal" scripts/*.py`

Expected: zero matches outside the scanner's own banned-name lists in `self_test.py`.

- [ ] **Step 5: File length check**

Run: `wc -l P:/Work/Programming/_Claude_Skills/context-analyser/scripts/*.py`

Expected: each file < 500 lines.

- [ ] **Step 6: Commit verification log**

No code changes expected. If issues were found and fixed, commit fixes:

```bash
git add -A
git commit -m "fix: address security verification findings"
```

---

### Task 6: Validate Token Budgets

**Files:**
- Read: all reference files + SKILL.md

- [ ] **Step 1: Run budget validation**

Run:

```bash
cd P:/Work/Programming/_Claude_Skills/context-analyser && python -c "
from scripts.count_tokens import count_tokens
from pathlib import Path

files = [
    ('references/compression.md', 800),
    ('references/restructuring.md', 800),
    ('references/layered-architecture.md', 1200),
    ('references/tiering.md', 800),
    ('references/context-rot-thresholds.md', 600),
    ('references/boundary-score.md', 1000),
]
all_ok = True
for f, budget in files:
    content = Path(f).read_text(encoding='utf-8')
    tokens = count_tokens(content)[0]
    status = 'OK' if tokens < budget else 'OVER'
    if status == 'OVER': all_ok = False
    print(f'{status:>5} {tokens:>5}/{budget:>5}  {f}')

# SKILL.md body only
content = Path('SKILL.md').read_text(encoding='utf-8')
body = content.split('---', 2)[2] if content.count('---') >= 2 else content
tokens = count_tokens(body)[0]
status = 'OK' if tokens < 500 else 'OVER'
if status == 'OVER': all_ok = False
print(f'{status:>5} {tokens:>5}/{500:>5}  SKILL.md (body)')

# Max concurrent
import sys
largest_ref = max(count_tokens(Path(f).read_text(encoding='utf-8'))[0] for f, _ in files)
skill_body = count_tokens(body)[0]
concurrent = skill_body + largest_ref
c_status = 'OK' if concurrent < 1700 else 'OVER'
if c_status == 'OVER': all_ok = False
print(f'{c_status:>5} {concurrent:>5}/{1700:>5}  Max concurrent (SKILL.md + largest ref)')

print()
print('ALL BUDGETS OK' if all_ok else 'BUDGET VIOLATIONS FOUND')
sys.exit(0 if all_ok else 1)
"
```

Expected: `ALL BUDGETS OK`

- [ ] **Step 2: Commit if any trimming was needed**

---

### Task 7: Integration Test -- Full Audit Pipeline

**Files:**
- Read: `scripts/count_tokens.py`, `tests/fixtures/sample_claude_bloated.md`

- [ ] **Step 1: Run audit on bloated fixture**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/count_tokens.py tests/fixtures/sample_claude_bloated.md`

Expected: Report showing ORANGE or RED zone, with per-section breakdown, tier recommendations, and projected outcome showing significant reduction.

- [ ] **Step 2: Run audit on GREEN fixture**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/count_tokens.py tests/fixtures/sample_claude.md`

Expected: Report showing GREEN zone, "No action needed."

- [ ] **Step 3: Run audit with JSON output**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/count_tokens.py tests/fixtures/sample_claude_bloated.md --json | python -m json.tool`

Expected: Valid JSON with all required fields.

- [ ] **Step 4: Run boundary check on valid action**

Run:

```bash
cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/boundary_check.py --semantic "You should always make sure to use parameterised queries when writing SQL." "Parameterised SQL only."
```

Expected: Exit 0. JSON shows `passed: true`.

- [ ] **Step 5: Run boundary check on unsafe rewrite**

Run:

```bash
cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/boundary_check.py --semantic "Never use eval() in production code." "Use eval() in production code."
```

Expected: Exit 1. JSON shows `passed: false`, negation dropped.

- [ ] **Step 6: Commit integration test results as a verification log**

No code changes. If bugs found, fix and commit:

```bash
git add -A
git commit -m "fix: address integration test findings"
```

---

### Task 8: Initialize Git Repository

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Check if git is already initialized**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && git status 2>/dev/null || echo "Not a git repo"`

- [ ] **Step 2: Initialize if needed**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && git init`

- [ ] **Step 3: Create .gitignore**

Create `.gitignore`:

```
__pycache__/
*.pyc
.claude/backups/
*.tmp
```

- [ ] **Step 4: Initial commit with all files**

```bash
git add .gitignore SKILL.md scripts/ references/ tests/ docs/
git commit -m "feat: context-analyser skill v1 - scaffold, scripts, tests, and reference docs"
```

---

### Task 9: Final Success Criteria Checklist

Run through all 8 success criteria from the spec:

- [ ] **Step 1: Criterion 1 -- /audit produces accurate reports**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/count_tokens.py tests/fixtures/sample_claude_bloated.md`

Verify: report shows sections, zones, tiers, projections.

- [ ] **Step 2: Criterion 4 -- SKILL.md body < 500 tokens**

Run:

```bash
cd P:/Work/Programming/_Claude_Skills/context-analyser && python -c "
from scripts.count_tokens import count_tokens; from pathlib import Path
body = Path('SKILL.md').read_text().split('---', 2)[2]
t = count_tokens(body)[0]
print(f'SKILL.md body: {t} tokens - {\"PASS\" if t < 500 else \"FAIL\"}')"
```

- [ ] **Step 3: Criterion 5 -- Max concurrent < 1,700**

Already verified in Task 6 Step 1.

- [ ] **Step 4: Criterion 6 -- Python zero deps, passes AST scan**

Run: `cd P:/Work/Programming/_Claude_Skills/context-analyser && python scripts/self_test.py`

Expected: `ALL FILES PASS SECURITY SCAN`

- [ ] **Step 5: Criterion 8 -- self_test.py exits 0**

Same as Step 4. Verify exit code is 0.

- [ ] **Step 6: All tests pass**

Run:

```bash
cd P:/Work/Programming/_Claude_Skills/context-analyser && python tests/test_count_tokens.py && python tests/test_boundary_check.py && python scripts/self_test.py
```

Expected: All three pass with exit code 0.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "chore: all success criteria verified, v1 complete"
```

---

## Spec Coverage Check

| Spec Requirement | Task(s) |
|---|---|
| count_tokens.sh exact API count | Task 4 |
| count_tokens.py within 6% | Task 2, Task 4 (agreement test) |
| self_test.py scans and passes | Task 5 |
| boundary_check.py semantic checks | Task 3 |
| Reference docs within budgets | Task 6 |
| SKILL.md body < 500 tokens | Task 6, Task 9 |
| Max concurrent < 1,700 | Task 6 |
| Audit report format | Task 7 |
| Boundary score system | Task 3 |
| Security policy compliance | Task 5 |
| All success criteria | Task 9 |

**Not covered by this plan (out of scope per spec Section 10):**
- Session-start hook
- Diff tracking
- Multi-file scanning
- Custom thresholds
- Per-edit accept/reject

**Also not tested in this plan (skill-level behaviour):**
- Phases 1-3 (compress/restructure/tier) are executed by the model reading reference docs, not by scripts. Testing requires running the skill in a Claude Code session with a real CLAUDE.md. This is manual QA, not automatable unit tests.
- Criterion 2 (full pipeline ORANGE->GREEN) and Criterion 3 (all boundary checks in live operation) require live skill execution.

#!/usr/bin/env python3
"""
Unit tests for scripts/scan_project.py (the /project-scan resting-context scanner).
No external test framework — uses a simple pass/fail runner that BOTH records
AND raises on failure so the gate is honest.
Run with: python3 tests/test_scan_project.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Allow importing from scripts/
sys.path.insert(
    0, str(Path(__file__).parent.parent / "skills" / "context-analyser" / "scripts")
)

from scan_project import (
    scan_project,
    format_report,
    _MCP_TOKENS_PER_TOOL,
)
from count_tokens import _validate_path, _classify_zone

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = str(FIXTURES / "sample_project")
CYCLE = str(FIXTURES / "cycle_project")
MISSING = str(FIXTURES / "missing_import_project")

# ── helpers ─────────────────────────────────────────────────────────────────

_results: list[tuple[str, bool, str]] = []


def _assert(name: str, condition: bool, msg: str = "") -> None:
    _results.append((name, bool(condition), msg))
    if not condition:
        detail = f" — {msg}" if msg else ""
        print(f"  FAIL  {name}{detail}")
        raise AssertionError(name + (": " + msg if msg else ""))
    else:
        print(f"  pass  {name}")


def _scan(path: str, **kw):
    """Scan with globals/plugins off by default so host config never leaks in."""
    kw.setdefault("include_global", False)
    kw.setdefault("include_mcp", True)
    return scan_project(path, **kw)


def _by_category(manifest: dict, category: str) -> list[dict]:
    return [s for s in manifest["sources"] if s["category"] == category]


# ── 1. manifest shape / keys ──────────────────────────────────────────────────

def test_manifest_shape() -> None:
    print("\n[1] manifest shape / keys")

    m = _scan(SAMPLE)

    required = {
        "project_root", "resting_baseline_tokens", "measured_tokens",
        "estimated_tokens", "resting_zone", "resting_action",
        "on_demand_pool_tokens", "sources", "mcp", "method", "notes",
    }
    _assert(
        "manifest has all required top-level keys",
        required.issubset(m.keys()),
        f"missing: {required - set(m.keys())}",
    )
    _assert("method is 'scan_project'", m["method"] == "scan_project", f"got {m['method']!r}")
    _assert("notes is a list", isinstance(m["notes"], list))
    _assert("sources is a list", isinstance(m["sources"], list))
    _assert("project_root resolved is absolute", Path(m["project_root"]).is_absolute())

    # Every source entry carries the documented schema.
    src_keys = {"name", "path", "category", "load", "tokens", "measured", "zone"}
    _assert(
        "every source has the documented keys",
        all(src_keys.issubset(s.keys()) for s in m["sources"]),
        "a source is missing one of name/path/category/load/tokens/measured/zone",
    )
    _assert(
        "every source tokens is an int >= 0",
        all(isinstance(s["tokens"], int) and s["tokens"] >= 0 for s in m["sources"]),
    )
    _assert(
        "every source measured is a bool",
        all(isinstance(s["measured"], bool) for s in m["sources"]),
    )


# ── 2. sources sorted descending by tokens ────────────────────────────────────

def test_sources_sorted() -> None:
    print("\n[2] sources sorted descending")

    m = _scan(SAMPLE)
    _assert(
        "sources sorted by tokens descending",
        all(
            m["sources"][i]["tokens"] >= m["sources"][i + 1]["tokens"]
            for i in range(len(m["sources"]) - 1)
        ),
        "sources not in descending token order",
    )


# ── 3. @import resolution (basic) ─────────────────────────────────────────────

def test_import_resolution() -> None:
    print("\n[3] @import resolution")

    m = _scan(SAMPLE)
    imports = _by_category(m, "import")

    _assert(
        "exactly one resolved import present",
        len(imports) == 1,
        f"got {len(imports)}: {[s['name'] for s in imports]}",
    )
    imp = imports[0]
    _assert("imported file is named imported.md", imp["name"] == "imported.md", f"got {imp['name']!r}")
    _assert("import inherits always load timing", imp["load"] == "always", f"got {imp['load']!r}")
    _assert("import is measured", imp["measured"] is True)
    _assert("import has positive tokens", imp["tokens"] > 0, f"got {imp['tokens']}")
    _assert("no missing-import notes for the clean fixture", m["notes"] == [], f"got {m['notes']}")


# ── 4. @import cycle does not crash ───────────────────────────────────────────

def test_import_cycle() -> None:
    print("\n[4] @import cycle is safe")

    # Must terminate (seen-set), not recurse forever.
    m = _scan(CYCLE)
    imports = _by_category(m, "import")
    claude = _by_category(m, "claude_md")

    _assert("cycle: root CLAUDE.md counted once", len(claude) == 1, f"got {len(claude)}")
    _assert(
        "cycle: import resolved exactly once (no infinite recursion)",
        len(imports) == 1,
        f"got {len(imports)}: {[s['name'] for s in imports]}",
    )
    _assert("cycle: scan returns a baseline int", isinstance(m["resting_baseline_tokens"], int))
    _assert("cycle: baseline > 0", m["resting_baseline_tokens"] > 0)


# ── 5. missing @import is skipped + noted, no crash ───────────────────────────

def test_missing_import() -> None:
    print("\n[5] missing @import skipped + noted")

    m = _scan(MISSING)
    imports = _by_category(m, "import")

    _assert("missing-import: no import entry created", len(imports) == 0, f"got {len(imports)}")
    _assert(
        "missing-import: a note records the skip",
        any("Missing @import" in n for n in m["notes"]),
        f"notes: {m['notes']}",
    )
    _assert(
        "missing-import: root still has its own tokens",
        m["resting_baseline_tokens"] > 0,
        f"got {m['resting_baseline_tokens']}",
    )


# ── 6. resting baseline == sum of always-loaded only ──────────────────────────

def test_resting_baseline() -> None:
    print("\n[6] resting baseline = always-loaded only")

    m = _scan(SAMPLE)

    always = [s for s in m["sources"] if s["load"] == "always"]
    not_always = [s for s in m["sources"] if s["load"] != "always"]

    _assert("there are always-loaded sources", len(always) > 0)
    _assert("there are non-always sources", len(not_always) > 0)

    expected_baseline = sum(s["tokens"] for s in always)
    _assert(
        "resting_baseline == sum(always tokens)",
        m["resting_baseline_tokens"] == expected_baseline,
        f"baseline={m['resting_baseline_tokens']} expected={expected_baseline}",
    )

    expected_pool = sum(s["tokens"] for s in not_always)
    _assert(
        "on_demand_pool == sum(non-always tokens)",
        m["on_demand_pool_tokens"] == expected_pool,
        f"pool={m['on_demand_pool_tokens']} expected={expected_pool}",
    )

    # The on-demand pool must be entirely excluded from the baseline.
    _assert(
        "no non-always source contributes to baseline",
        all(s["load"] == "always" for s in always),
    )


# ── 7. measured vs estimated split ────────────────────────────────────────────

def test_measured_estimated_split() -> None:
    print("\n[7] measured vs estimated split")

    m = _scan(SAMPLE)
    always = [s for s in m["sources"] if s["load"] == "always"]

    expected_measured = sum(s["tokens"] for s in always if s["measured"])
    expected_estimated = sum(s["tokens"] for s in always if not s["measured"])

    _assert(
        "measured_tokens == sum(always & measured)",
        m["measured_tokens"] == expected_measured,
        f"got {m['measured_tokens']} expected {expected_measured}",
    )
    _assert(
        "estimated_tokens == sum(always & not measured)",
        m["estimated_tokens"] == expected_estimated,
        f"got {m['estimated_tokens']} expected {expected_estimated}",
    )
    _assert(
        "measured + estimated == resting_baseline",
        m["measured_tokens"] + m["estimated_tokens"] == m["resting_baseline_tokens"],
        f"{m['measured_tokens']} + {m['estimated_tokens']} != {m['resting_baseline_tokens']}",
    )
    # On a disk-only scan the fixture has no MCP tools, so estimated stays 0.
    _assert(
        "fixture has no estimated tokens (disk-only, no MCP tools)",
        m["estimated_tokens"] == 0,
        f"got {m['estimated_tokens']}",
    )
    _assert(
        "all measured always-sources are flagged measured=True",
        all(s["measured"] is True for s in always),
    )


# ── 8. skill / agent description-vs-body separation ───────────────────────────

def test_desc_vs_body_separation() -> None:
    print("\n[8] skill/agent description vs body separation")

    m = _scan(SAMPLE)

    skill_desc = _by_category(m, "skill_desc")
    skill_body = _by_category(m, "skill_body")
    agent_desc = _by_category(m, "agent_desc")
    agent_body = _by_category(m, "agent_body")

    _assert("one skill description entry", len(skill_desc) == 1, f"got {len(skill_desc)}")
    _assert("one skill body entry", len(skill_body) == 1, f"got {len(skill_body)}")
    _assert("one agent description entry", len(agent_desc) == 1, f"got {len(agent_desc)}")
    _assert("one agent body entry", len(agent_body) == 1, f"got {len(agent_body)}")

    _assert("skill description loads always", skill_desc[0]["load"] == "always", f"got {skill_desc[0]['load']!r}")
    _assert("skill body loads on-trigger", skill_body[0]["load"] == "on-trigger", f"got {skill_body[0]['load']!r}")
    _assert("agent description loads always", agent_desc[0]["load"] == "always", f"got {agent_desc[0]['load']!r}")
    _assert("agent body loads on-demand/on-trigger", agent_body[0]["load"] in ("on-demand", "on-trigger"), f"got {agent_body[0]['load']!r}")

    # Descriptions feed the baseline; bodies must not.
    _assert(
        "skill description counts toward baseline (always)",
        skill_desc[0]["load"] == "always",
    )
    _assert(
        "skill body excluded from baseline (not always)",
        skill_body[0]["load"] != "always",
    )
    _assert("skill description has tokens", skill_desc[0]["tokens"] > 0)
    _assert("skill body has tokens", skill_body[0]["tokens"] > 0)


# ── 9. nested CLAUDE.md classified conditional (not in baseline) ──────────────

def test_nested_claude_md_conditional() -> None:
    print("\n[9] nested CLAUDE.md is conditional, not baseline")

    m = _scan(SAMPLE)
    nested = _by_category(m, "nested_claude_md")

    _assert("exactly one nested CLAUDE.md found", len(nested) == 1, f"got {len(nested)}")
    n = nested[0]
    _assert("nested CLAUDE.md load is conditional", n["load"] == "conditional", f"got {n['load']!r}")
    _assert("nested entry name references sub/", "sub" in n["name"], f"got {n['name']!r}")
    _assert("nested CLAUDE.md has tokens", n["tokens"] > 0)
    _assert(
        "nested CLAUDE.md NOT counted in resting baseline",
        n["tokens"] not in (m["resting_baseline_tokens"],)
        and n["load"] != "always",
        "nested file should be conditional, never always",
    )
    # Prove the root CLAUDE.md (always) and nested (conditional) are distinct.
    root_md = _by_category(m, "claude_md")
    _assert("root CLAUDE.md present and always", len(root_md) == 1 and root_md[0]["load"] == "always")


# ── 10. MCP block present + labelled estimated ────────────────────────────────

def test_mcp_block() -> None:
    print("\n[10] MCP block present + estimated")

    m = _scan(SAMPLE, include_mcp=True)
    mcp = m["mcp"]

    mcp_keys = {"method", "servers_found", "server_names", "tokens_per_tool", "estimated_tokens", "note"}
    _assert("MCP block has all keys", mcp_keys.issubset(mcp.keys()), f"missing: {mcp_keys - set(mcp.keys())}")
    _assert("MCP servers_found is int", isinstance(mcp["servers_found"], int))
    _assert("MCP server_names is list", isinstance(mcp["server_names"], list))
    _assert(
        "MCP tokens_per_tool == documented heuristic",
        mcp["tokens_per_tool"] == _MCP_TOKENS_PER_TOOL == 300,
        f"got {mcp['tokens_per_tool']}",
    )
    _assert(
        "MCP estimated_tokens is 0 from disk-only scan",
        mcp["estimated_tokens"] == 0,
        f"got {mcp['estimated_tokens']}",
    )
    _assert(
        "MCP note flags it as runtime-only / not measurable from disk",
        "runtime" in mcp["note"].lower() and "disk" in mcp["note"].lower(),
        f"note: {mcp['note']!r}",
    )

    # Any MCP source that lands in the manifest must be marked NOT measured.
    mcp_sources = _by_category(m, "mcp")
    _assert(
        "any MCP source entry is marked measured=False (estimated)",
        all(s["measured"] is False for s in mcp_sources),
        "an MCP source is wrongly marked measured",
    )

    # --no-mcp path: block still present, clearly skipped.
    m2 = _scan(SAMPLE, include_mcp=False)
    _assert("MCP block present even when skipped", "mcp" in m2 and isinstance(m2["mcp"], dict))
    _assert("skipped MCP estimated_tokens is 0", m2["mcp"]["estimated_tokens"] == 0)


# ── 11. zone reuse (single source of truth) ───────────────────────────────────

def test_zone_reuse() -> None:
    print("\n[11] zone classification reuse")

    m = _scan(SAMPLE)

    # Resting zone must match the shared classifier on the baseline.
    expected_zone, expected_action = _classify_zone(m["resting_baseline_tokens"])
    _assert(
        "resting_zone matches _classify_zone(baseline)",
        m["resting_zone"] == expected_zone,
        f"got {m['resting_zone']!r} expected {expected_zone!r}",
    )
    _assert(
        "resting_action matches _classify_zone(baseline)",
        m["resting_action"] == expected_action,
        f"got {m['resting_action']!r}",
    )
    # Small fixture should be GREEN.
    _assert("fixture resting zone is GREEN", m["resting_zone"] == "GREEN", f"got {m['resting_zone']}")

    # Per-source zones must equal the shared classifier on their own tokens.
    _assert(
        "every source zone == _classify_zone(its tokens)",
        all(s["zone"] == _classify_zone(s["tokens"])[0] for s in m["sources"]),
        "a source zone disagrees with the shared classifier",
    )


# ── 12. path outside allowed roots raises; scanner stays safe ─────────────────

def test_out_of_root() -> None:
    print("\n[12] out-of-root path containment")

    # The validation primitive the scanner reuses MUST reject out-of-root files.
    raised = False
    try:
        _validate_path("/etc/hosts")
    except ValueError:
        raised = True
    _assert(
        "_validate_path raises ValueError for a file outside allowed roots",
        raised,
        "no ValueError raised for /etc/hosts",
    )

    # And the read-only scanner must not crash on an out-of-root root: it
    # validates every read, so an out-of-root tree yields an empty manifest.
    m = scan_project("/etc", include_global=False, include_mcp=False)
    _assert(
        "scan_project on out-of-root tree returns empty baseline (no crash)",
        m["resting_baseline_tokens"] == 0 and m["sources"] == [],
        f"baseline={m['resting_baseline_tokens']} sources={len(m['sources'])}",
    )
    _assert(
        "out-of-root scan records a no-sources note",
        any("No always-loaded" in n for n in m["notes"]),
        f"notes: {m['notes']}",
    )


# ── 13. format_report renders the headline + sections ─────────────────────────

def test_format_report() -> None:
    print("\n[13] format_report rendering")

    m = _scan(SAMPLE)
    report = format_report(m)

    _assert("report is a non-empty string", isinstance(report, str) and len(report) > 0)
    _assert("report leads with the resting baseline", "RESTING BASELINE" in report)
    _assert("report shows measured vs estimated", "Measured" in report and "Estimated" in report)
    _assert("report shows the on-demand pool", "On-demand pool" in report)
    _assert("report has a source breakdown section", "SOURCE BREAKDOWN" in report)
    _assert("report has an MCP section", "MCP" in report)
    _assert(
        "report shows the baseline number",
        str(m["resting_baseline_tokens"]) in report,
        "baseline value not present in report text",
    )


# ── Runner ───────────────────────────────────────────────────────────────────

def main() -> None:
    test_fns = [
        test_manifest_shape,
        test_sources_sorted,
        test_import_resolution,
        test_import_cycle,
        test_missing_import,
        test_resting_baseline,
        test_measured_estimated_split,
        test_desc_vs_body_separation,
        test_nested_claude_md_conditional,
        test_mcp_block,
        test_zone_reuse,
        test_out_of_root,
        test_format_report,
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

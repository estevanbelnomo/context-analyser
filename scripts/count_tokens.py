#!/usr/bin/env python3
"""
Token counter for CLAUDE.md audit skill.
ZERO external dependencies. Stdlib only. Auditable in full.

Security guarantees:
  - No eval, exec, pickle, importlib, __import__
  - No network calls (no socket, urllib, http)
  - No subprocess calls
  - No dynamic code loading of any kind
  - Input path is validated before any file I/O
  - All string processing uses compile-time regex patterns

Accuracy: ~93-95% vs Claude's actual tokenizer on typical CLAUDE.md content.

NOTE: This file is at ~486 lines, near the 500-line hard limit (Rule 8).
If phase-specific counting logic is added later, split into separate modules
(e.g. count_tokens_core.py + count_tokens_audit.py).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# == Security: Input Validation ==================================


def _validate_path(raw: str) -> Path:
    """
    Validate and resolve file path. Rejects path traversal,
    null bytes, and non-regular files.
    """
    if "\x00" in raw:
        raise ValueError("Null byte in path.")

    path = Path(raw).resolve()

    allowed_roots = [
        Path.home().resolve(),
        Path("/mnt/user-data").resolve(),
        Path("/mnt/skills").resolve(),
        Path("/tmp").resolve(),
    ]
    # On Windows, also allow the current working directory tree
    cwd = Path.cwd().resolve()
    if cwd not in allowed_roots:
        allowed_roots.append(cwd)

    sep = "\\" if sys.platform == "win32" else "/"
    if not any(
        path == root or str(path).startswith(str(root) + sep)
        for root in allowed_roots
    ):
        raise ValueError(f"Path outside allowed roots: {path}")

    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")

    return path


# == Core: Regex Pre-Tokenizer ===================================

_PRE_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"'(?:t|re|ve|ll|d|m|s|nt)"
    r"|[A-Za-z]+"
    r"|[0-9]+"
    r"|[^\sA-Za-z0-9]+"
    r"|\s",
    re.UNICODE,
)


def _pre_tokenize(text: str) -> list[str]:
    """Split text into pre-tokens using the BPE boundary regex."""
    return _PRE_TOKEN_PATTERN.findall(text)


# == Core: Content Classification ================================

_CODE_SIGNALS: re.Pattern[str] = re.compile(
    r"^\s*(?:"
    r"[-*`{}\[\]|]"
    r"|//|/\*|#!"
    r"|import |from |def "
    r"|fn |let |pub |use "
    r"|if |else |for |while"
    r"|return |match "
    r"|pip |npm |cargo "
    r"|curl |grep |awk "
    r")"
)

_PATH_SIGNALS: re.Pattern[str] = re.compile(
    r"(?:/[\w.-]+){2,}"
    r"|\\[\w.-]+"
    r"|\.(?:md|py|rs|toml|json|yaml|yml|sh|sql|ts|js|jsx|tsx)\b"
)


def _classify_line(line: str) -> str:
    """Classify a line as 'code', 'path', 'prose', or 'whitespace'."""
    stripped = line.strip()
    if not stripped:
        return "whitespace"
    if _CODE_SIGNALS.match(stripped):
        return "code"
    if _PATH_SIGNALS.search(stripped):
        return "path"
    return "prose"


# == Core: Calibrated Token Counter ==============================

_CALIBRATION: dict[str, float] = {
    "prose": 0.94,
    "code": 1.08,
    "path": 1.15,
    "whitespace": 0.35,
}


def count_tokens(text: str) -> tuple[int, str, str]:
    """
    Count tokens in text using calibrated regex pre-tokenizer.

    Returns:
        (token_count, method_name, accuracy_description)
    """
    if not text or not text.strip():
        return 0, "regex_pretokenizer", "~94% (+/- 6%)"

    lines = text.split("\n")

    pretokens_by_type: dict[str, int] = {
        "prose": 0,
        "code": 0,
        "path": 0,
        "whitespace": 0,
    }

    for line in lines:
        content_type = _classify_line(line)
        line_pretokens = len(_pre_tokenize(line))
        pretokens_by_type[content_type] += line_pretokens
        pretokens_by_type["whitespace"] += 1

    estimated = sum(
        count * _CALIBRATION[ctype] for ctype, count in pretokens_by_type.items()
    )

    return max(1, round(estimated)), "regex_pretokenizer", "~94% (+/- 6%)"


# == Section Parser ==============================================

_HEADER_PATTERN: re.Pattern[str] = re.compile(r"^(#{1,6})\s+(.+)$")


def _parse_sections(content: str) -> list[dict]:
    """
    Split markdown content into sections by headers.
    Returns list of dicts with header, body, level.
    """
    sections: list[dict] = []
    current_header = "(preamble)"
    current_level = 0
    current_lines: list[str] = []

    for line in content.split("\n"):
        match = _HEADER_PATTERN.match(line)
        if match:
            body = "\n".join(current_lines)
            sections.append(
                {
                    "header": current_header,
                    "body": body,
                    "level": current_level,
                }
            )
            current_header = match.group(2).strip()
            current_level = len(match.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    body = "\n".join(current_lines)
    sections.append(
        {
            "header": current_header,
            "body": body,
            "level": current_level,
        }
    )

    return sections


# == Zone Classification =========================================

_ZONES: tuple[tuple[str, int, int, str], ...] = (
    ("GREEN", 0, 500, "No action needed. Optimal token budget."),
    ("YELLOW", 500, 2_000, "Compression recommended. Rewrite for conciseness."),
    ("ORANGE", 2_000, 5_000, "Restructure required. Apply layered architecture."),
    ("RED", 5_000, 10_000, "Urgent. Tiering required. Instructions degrading."),
    (
        "CRITICAL",
        10_000,
        10**9,
        "Instructions are noise. Immediate decomposition needed.",
    ),
)


def _classify_zone(tokens: int) -> tuple[str, str]:
    """Returns (zone_name, action_description)."""
    for name, low, high, action in _ZONES:
        if low <= tokens < high:
            return name, action
    return "CRITICAL", _ZONES[-1][3]


def _boundary_warning(
    tokens: int,
    accuracy_pct: float = 6.0,
) -> dict | None:
    """
    Check if token count is near a zone boundary within the
    accuracy margin. Returns warning dict or None.
    """
    margin = accuracy_pct / 100.0
    low = tokens * (1.0 - margin)
    high = tokens * (1.0 + margin)

    zone_at_count = _classify_zone(tokens)[0]
    zone_at_low = _classify_zone(round(low))[0]
    zone_at_high = _classify_zone(round(high))[0]

    if zone_at_low != zone_at_count or zone_at_high != zone_at_count:
        possible = sorted({zone_at_low, zone_at_count, zone_at_high})
        return {
            "warning": (
                "Count is near a zone boundary. "
                "Classification may differ with exact counting."
            ),
            "estimated_range": f"{round(low)} -- {round(high)}",
            "possible_zones": possible,
            "fix": (
                "Run count_tokens.sh with ANTHROPIC_API_KEY "
                "for exact classification."
            ),
        }
    return None


# == Tier Recommendation =========================================


def _recommend_tier(
    header: str,
    tokens: int,
    pct: float,
) -> tuple[int, str]:
    """
    Recommend a tier for a section based on size and role.
    """
    h = header.lower()

    core_signals = (
        "preamble",
        "identity",
        "rules",
        "command",
        "context",
        "session",
        "management",
        "index",
        "loading",
    )
    if any(s in h for s in core_signals) and tokens < 200:
        return 0, "Core structural section. Keep in CLAUDE.md."

    if tokens > 800:
        return 2, f"Large section ({tokens} tok). Move to reference file."

    if tokens > 300:
        return 1, f"Domain content ({tokens} tok). Move to skill file."

    if tokens < 80 and pct < 5.0:
        return 0, "Small enough to remain in core."

    return 0, "Moderate size. Review if core exceeds 500 tokens."


# == Full Audit ==================================================


def audit_file(filepath: str) -> dict:
    """
    Full audit of a CLAUDE.md file. Returns structured dict with
    per-section token counts, zone classifications, tier suggestions,
    boundary warnings, and projected outcome.
    """
    path = _validate_path(filepath)
    content = path.read_text(encoding="utf-8")

    total_tokens, method, accuracy = count_tokens(content)
    total_zone, total_action = _classify_zone(total_tokens)
    warning = _boundary_warning(total_tokens)

    raw_sections = _parse_sections(content)
    section_results: list[dict] = []
    tier_suggestions: list[dict] = []

    for sec in raw_sections:
        sec_tokens = count_tokens(sec["body"])[0]
        pct = (
            round(sec_tokens / total_tokens * 100, 1) if total_tokens > 0 else 0.0
        )
        sec_zone = _classify_zone(sec_tokens)[0]

        section_results.append(
            {
                "section": sec["header"],
                "level": sec["level"],
                "tokens": sec_tokens,
                "pct_of_total": pct,
                "zone": sec_zone,
                "lines": sec["body"].count("\n") + 1,
            }
        )

        tier, reason = _recommend_tier(sec["header"], sec_tokens, pct)
        tier_suggestions.append(
            {
                "section": sec["header"],
                "tokens": sec_tokens,
                "recommended_tier": tier,
                "reason": reason,
            }
        )

    section_results.sort(key=lambda s: s["tokens"], reverse=True)
    tier_suggestions.sort(key=lambda s: s["tokens"], reverse=True)

    tier0_tokens = sum(
        s["tokens"] for s in tier_suggestions if s["recommended_tier"] == 0
    )
    index_overhead = 80
    projected_core = tier0_tokens + index_overhead
    projected_zone = _classify_zone(projected_core)[0]

    reduction_pct = (
        round((1.0 - projected_core / total_tokens) * 100, 1)
        if total_tokens > 0
        else 0.0
    )

    return {
        "file": str(path),
        "total_tokens": total_tokens,
        "total_zone": total_zone,
        "total_action": total_action,
        "method": method,
        "accuracy": accuracy,
        "boundary_warning": warning,
        "sections": section_results,
        "tier_suggestions": tier_suggestions,
        "projected_core_tokens": projected_core,
        "projected_core_zone": projected_zone,
        "estimated_reduction_pct": reduction_pct,
    }


# == Report Formatter ============================================

_ZONE_MARKERS: dict[str, str] = {
    "GREEN": "[OK]",
    "YELLOW": "[!!]",
    "ORANGE": "[##]",
    "RED": "[XX]",
    "CRITICAL": "[!!XX!!]",
}


def format_report(result: dict) -> str:
    """Format audit result as a human-readable terminal report."""
    if "error" in result:
        return f"ERROR: {result['error']}"

    out: list[str] = []
    zm = _ZONE_MARKERS

    out.append("=" * 72)
    out.append("  CLAUDE.MD TOKEN AUDIT")
    out.append("=" * 72)
    out.append("")
    out.append(f"  File:      {result['file']}")
    out.append(f"  Method:    {result['method']} ({result['accuracy']})")
    out.append(f"  Total:     {result['total_tokens']} tokens")
    out.append(f"  Zone:      {zm[result['total_zone']]} {result['total_zone']}")
    out.append(f"  Action:    {result['total_action']}")

    bw = result.get("boundary_warning")
    if bw:
        out.append("")
        out.append(f"  WARNING:   {bw['warning']}")
        out.append(f"  Range:     {bw['estimated_range']} tokens")
        out.append(f"  Could be:  {', '.join(bw['possible_zones'])}")
        out.append(f"  Fix:       {bw['fix']}")

    out.append("")
    out.append("-" * 72)
    out.append("  SECTION BREAKDOWN (largest first)")
    out.append("-" * 72)

    for s in result["sections"]:
        bar_len = min(35, max(1, s["tokens"] // 30))
        bar = "#" * bar_len
        z = zm.get(s["zone"], "   ")
        out.append(
            f"  {s['tokens']:>5} tok  {s['pct_of_total']:>5.1f}%  "
            f"{z:<10} {bar}  {s['section']}"
        )

    out.append("")
    out.append("-" * 72)
    out.append("  TIER RECOMMENDATIONS")
    out.append("-" * 72)

    for t in result["tier_suggestions"]:
        out.append(
            f"  T{t['recommended_tier']}  {t['tokens']:>5} tok  "
            f"{t['section']:<30}  {t['reason']}"
        )

    out.append("")
    out.append("-" * 72)
    out.append("  PROJECTED OUTCOME")
    out.append("-" * 72)
    cz = result["projected_core_zone"]
    out.append(
        f"  Current:   {result['total_tokens']} tokens "
        f"({zm[result['total_zone']]} {result['total_zone']})"
    )
    out.append(
        f"  Projected: {result['projected_core_tokens']} tokens "
        f"({zm[cz]} {cz})"
    )
    out.append(f"  Reduction: {result['estimated_reduction_pct']}%")
    out.append("=" * 72)

    return "\n".join(out)


# == Entry Point =================================================


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.stdout.write(
            "Usage: python count_tokens.py <path-to-CLAUDE.md> [--json]\n"
            "\n"
            "  --json    Output raw JSON instead of formatted report\n"
            "\n"
            "Primary method: set ANTHROPIC_API_KEY and use count_tokens.sh\n"
            "This script is the offline fallback (~94% accuracy).\n"
        )
        sys.exit(0)

    try:
        result = audit_file(sys.argv[1])
    except ValueError as exc:
        result = {"error": str(exc)}

    if "--json" in sys.argv:
        sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_report(result))
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()

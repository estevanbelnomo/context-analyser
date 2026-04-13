#!/usr/bin/env python3
"""
Security self-test for context-analyser skill.
Scans all Python files in the scripts/ directory for policy violations.
Test files and spec documents are excluded from the scan to avoid false
positives from legitimate test-only imports (e.g. traceback, unittest).
Subdirectories of scripts/ are scanned recursively via rglob("*.py").
ZERO external dependencies. Stdlib only.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


# -- Permitted imports (Rule 1) --

_PERMITTED_MODULES: frozenset[str] = frozenset({
    "__future__",
    "ast",
    "json",
    "os",
    "re",
    "sys",
    "collections",
    "pathlib",
})

# -- Banned function calls (Rules 2, 4) --

_BANNED_CALLS: frozenset[str] = frozenset({
    "eval",
    "exec",
    "compile",
    "__import__",
    "breakpoint",
})

_BANNED_ATTR_CALLS: frozenset[tuple[str, str]] = frozenset({
    ("os", "system"),
    ("os", "popen"),
    ("os", "execl"),
    ("os", "execle"),
    ("os", "execlp"),
    ("os", "execlpe"),
    ("os", "execv"),
    ("os", "execve"),
    ("os", "execvp"),
    ("os", "execvpe"),
    ("os", "spawnl"),
    ("os", "spawnle"),
    ("os", "spawnlp"),
    ("os", "spawnlpe"),
    ("os", "spawnv"),
    ("os", "spawnve"),
    ("os", "spawnvp"),
    ("os", "spawnvpe"),
})

# -- Banned imports (Rules 3, 4, 5) --

_BANNED_MODULES: frozenset[str] = frozenset({
    # Network (Rule 3)
    "socket", "urllib", "http", "xmlrpc", "ftplib",
    "smtplib", "poplib", "imaplib", "ssl", "webbrowser",
    "requests", "httpx", "aiohttp",
    # Subprocess (Rule 4)
    "subprocess", "pty", "commands",
    # Dynamic loading (Rule 5)
    "importlib", "runpy", "zipimport", "pkgutil", "imp",
    # Dangerous serialisation (Rule 2)
    "pickle", "marshal", "ctypes", "cffi",
})

# -- Obfuscation detection (Rule 8) --

_B64_PATTERN: re.Pattern[str] = re.compile(r'["\'][A-Za-z0-9+/=]{64,}["\']')
_HEX_PATTERN: re.Pattern[str] = re.compile(r'["\'](?:\\x[0-9a-fA-F]{2}){8,}["\']')


def _module_rule(module: str) -> str:
    """Map a banned module to its governing rule."""
    network = {
        "socket", "urllib", "http", "xmlrpc", "ftplib",
        "smtplib", "poplib", "imaplib", "ssl", "webbrowser",
        "requests", "httpx", "aiohttp",
    }
    subprocess_mods = {"subprocess", "pty", "commands"}
    dynamic = {"importlib", "runpy", "zipimport", "pkgutil", "imp"}
    dangerous = {"pickle", "marshal", "ctypes", "cffi"}

    if module in network:
        return "Rule 3 (No network access)"
    if module in subprocess_mods:
        return "Rule 4 (No subprocess)"
    if module in dynamic:
        return "Rule 5 (No dynamic code loading)"
    if module in dangerous:
        return "Rule 2 (No dangerous builtins)"
    return "Unknown"


def _scan_file(filepath: Path) -> list[str]:
    """
    Scan a single Python file for security policy violations.
    Returns list of violation descriptions. Empty list = clean.
    """
    violations: list[str] = []

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"Cannot read file: {exc}"]

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as exc:
        return [f"Syntax error: {exc}"]

    for node in ast.walk(tree):

        # -- Check imports --

        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BANNED_MODULES:
                    violations.append(
                        f"Line {node.lineno}: Banned import '{alias.name}' "
                        f"(Rule: {_module_rule(root)})"
                    )
                elif root not in _PERMITTED_MODULES:
                    violations.append(
                        f"Line {node.lineno}: Unpermitted import '{alias.name}'. "
                        f"Only stdlib modules in the permitted list are allowed (Rule 1)."
                    )

        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in _BANNED_MODULES:
                violations.append(
                    f"Line {node.lineno}: Banned 'from {node.module} import ...' "
                    f"(Rule: {_module_rule(root)})"
                )
            elif root not in _PERMITTED_MODULES:
                violations.append(
                    f"Line {node.lineno}: Unpermitted 'from {node.module} import ...'. "
                    f"Only stdlib modules in the permitted list are allowed (Rule 1)."
                )

        # -- Check function calls --

        if isinstance(node, ast.Call):
            func = node.func

            if isinstance(func, ast.Name) and func.id in _BANNED_CALLS:
                violations.append(
                    f"Line {node.lineno}: Banned call to '{func.id}()' (Rule 2)"
                )

            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                pair = (func.value.id, func.attr)
                if pair in _BANNED_ATTR_CALLS:
                    violations.append(
                        f"Line {node.lineno}: Banned call to "
                        f"'{func.value.id}.{func.attr}()' (Rule 4)"
                    )

    # -- Check file length (Rule 8) --

    line_count = source.count("\n") + 1
    if line_count > 500:
        violations.append(
            f"File is {line_count} lines (hard limit: 500). "
            f"Split into smaller modules (Rule 8)."
        )

    # -- Check for base64/hex blobs (Rule 8) --

    for i, line in enumerate(source.split("\n"), 1):
        if _B64_PATTERN.search(line):
            violations.append(
                f"Line {i}: Suspicious base64-like string detected (Rule 8)"
            )
        if _HEX_PATTERN.search(line):
            violations.append(
                f"Line {i}: Suspicious hex-encoded string detected (Rule 8)"
            )

    return violations


def scan_skill_directory(skill_dir: Path) -> dict:
    """
    Scan all Python files in the skill directory.
    Returns structured results.
    """
    results: dict[str, list[str]] = {}
    all_clean = True

    for py_file in sorted(skill_dir.rglob("*.py")):
        violations = _scan_file(py_file)
        relative = str(py_file.relative_to(skill_dir))
        results[relative] = violations
        if violations:
            all_clean = False

    return {
        "all_clean": all_clean,
        "files": results,
    }


def format_scan_report(results: dict) -> str:
    """Format scan results as human-readable report."""
    out: list[str] = []

    out.append("=" * 72)
    out.append("  PYTHON SECURITY SCAN")
    out.append("=" * 72)
    out.append("")

    for filepath, violations in results["files"].items():
        if violations:
            out.append(f"  [FAIL] {filepath}")
            for v in violations:
                out.append(f"         {v}")
            out.append("")
        else:
            out.append(f"  [PASS] {filepath}")

    out.append("")
    out.append("-" * 72)

    if results["all_clean"]:
        out.append("  RESULT: ALL FILES PASS SECURITY SCAN")
    else:
        out.append("  RESULT: VIOLATIONS FOUND -- FIX BEFORE DEPLOYING")

    out.append("=" * 72)

    return "\n".join(out)


if __name__ == "__main__":
    # Scan only scripts/ directory — security policy applies to skill code,
    # not test harnesses which legitimately import non-permitted modules.
    skill_dir = Path(__file__).parent
    results = scan_skill_directory(skill_dir)
    sys.stdout.write(format_scan_report(results))
    sys.stdout.write("\n")
    sys.exit(0 if results["all_clean"] else 1)

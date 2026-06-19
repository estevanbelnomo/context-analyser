#!/usr/bin/env python3
"""
Full-project resting-context scanner for the context-analyser skill.

Inventories EVERY token loaded into every message at rest (before the user
types) -- the "resting context baseline" that sits on the context-rot curve --
plus a separate on-demand pool that loads only on trigger.

ZERO external deps. Stdlib only. READ-ONLY and STATELESS: writes NO files,
keeps NO state, touches NO network, spawns NO subprocess. All paths validated.
Reuses the single source of truth for tokenisation and zone thresholds:
    from count_tokens import count_tokens, _validate_path, _classify_zone
(count_tokens is __main__-guarded, so importing it has no side effects.)

Scope: only WHOLE-LINE @import directives are inventoried (inline @mentions are
out of scope); @import targets are contained to their originating tree (project
root, or ~/.claude for the global chain), so untrusted project content cannot
reach arbitrary files under $HOME. Near the 500-line cap (Rule 8); split if
adding source kinds.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from count_tokens import count_tokens, _validate_path, _classify_zone

# == Constants ===================================================

# Heuristic tokens per advertised MCP tool schema. Used ONLY by the interactive
# SKILL layer; from disk the tool count is unknown, so MCP estimate stays 0.
_MCP_TOKENS_PER_TOOL: int = 300

_MAX_IMPORT_DEPTH: int = 5  # @import recursion cap (also cycle-safe via seen-set)
_EST_MARK: str = "~est"     # report marker for estimated (not measured) tokens

# VCS/dependency/build/cache trees pruned during the nested-CLAUDE.md walk
# (a vendored CLAUDE.md is noise, not project config).
_PRUNED_DIRS: frozenset[str] = frozenset({
    ".git", "node_modules", ".venv", "venv", "dist", "build", ".tox",
    "__pycache__", ".mypy_cache", ".pytest_cache", "vendor", ".cache",
})

# == Module-level compiled regex ================================

# Whole-line @import directive (leading ws, "@", path, EOL); captures the path.
_IMPORT_PATTERN: re.Pattern[str] = re.compile(r"^[ \t]*@([^\s]+)\s*$", re.MULTILINE)

# Strips fenced code blocks so "@handle" in a fence is not read as an import.
_FENCE_PATTERN: re.Pattern[str] = re.compile(r"```.*?```", re.DOTALL)

# SKILL/agent frontmatter block (incl. --- delimiters) + a description: probe.
_FRONTMATTER_PATTERN: re.Pattern[str] = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_DESC_PATTERN: re.Pattern[str] = re.compile(r"^description:[ \t]*", re.MULTILINE)

# == Safe read helpers (read-only) ==============================

def _within(path: Path, base: Path) -> bool:
    """True iff resolved `path` is `base` or under it. Checked post-resolve, so
    it holds after symlink dereferencing -- keeps untrusted @import / symlink
    targets inside their tree, independent of _validate_path's broad roots."""
    p, b = str(path), str(base)
    return p == b or p.startswith(b + os.sep)


def _read_text(path: Path) -> str | None:
    """Validate + read text, returning None on any error. Read-only."""
    try:
        return _validate_path(str(path)).read_text(encoding="utf-8")
    except (ValueError, OSError, UnicodeDecodeError):
        return None


def _safe_token_count(path: Path) -> int:
    """Read a validated file and return its token count (0 on any error)."""
    text = _read_text(path)
    return count_tokens(text)[0] if text else 0


def _read_json(path: Path) -> object | None:
    """Validate + read + parse a JSON config file. None on any error."""
    text = _read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

# == @import resolution =========================================

def _resolve_import_target(spec: str, base_dir: Path) -> Path | None:
    """Resolve an @import spec to an absolute path. @~/x -> home-relative;
    @/x -> absolute; @x -> relative to importer. None for empty specs."""
    if not spec:
        return None
    if spec.startswith("~"):
        return (Path.home() / spec[1:].lstrip("/")).resolve()
    p = Path(spec)
    return p.resolve() if p.is_absolute() else (base_dir / spec).resolve()


def _collect_imports(
    start: Path, seen: set[str], notes: list[str], allowed_base: Path, depth: int = 0
) -> list[dict]:
    """Recursively resolve whole-line @import directives from `start`.
    Cycle-safe (shared `seen`), depth-capped, tolerant of missing targets.
    Untrusted-input containment: @import specs come from project content, so
    every resolved target MUST stay inside `allowed_base` (project tree, or
    ~/.claude for the global chain), independent of _validate_path's broader
    roots. Escaping/rejected targets are skipped with a distinct note, never
    read or silently zeroed."""
    if depth >= _MAX_IMPORT_DEPTH:
        return []
    text = _read_text(start)
    if text is None:
        return []
    scannable = _FENCE_PATTERN.sub("", text)
    entries: list[dict] = []
    for match in _IMPORT_PATTERN.finditer(scannable):
        spec = match.group(1)
        target = _resolve_import_target(spec, start.parent)
        if target is None:
            continue
        key = str(target)
        if key in seen:
            continue
        seen.add(key)
        if not _within(target, allowed_base):
            notes.append(f"@import outside allowed tree skipped: {spec}")
            continue
        if not target.is_file():
            notes.append(f"Missing @import skipped: {spec}")
            continue
        text_target = _read_text(target)
        if text_target is None:
            notes.append(f"Blocked @import outside allowed roots: {spec}")
            continue
        tokens = count_tokens(text_target)[0] if text_target.strip() else 0
        entries.append({
            "name": target.name, "path": key, "category": "import",
            "load": "always", "tokens": tokens, "measured": True,
            "zone": _classify_zone(tokens)[0],
        })
        entries.extend(_collect_imports(target, seen, notes, allowed_base, depth + 1))
    return entries

# == Source builders ============================================

def _entry(name: str, path: Path, category: str, load: str) -> dict:
    """Build one measured manifest source entry from a file path."""
    tokens = _safe_token_count(path)
    return {
        "name": name, "path": str(path), "category": category, "load": load,
        "tokens": tokens, "measured": True, "zone": _classify_zone(tokens)[0],
    }


def _add_claude_md_chain(
    sources, seen, notes, md_path: Path, name: str, load: str, allowed_base: Path
) -> None:
    """
    Add a CLAUDE.md-style file plus its resolved @import chain. `allowed_base`
    bounds @import resolution to a legitimate tree (project root, or ~/.claude).
    """
    if not md_path.is_file():
        return
    key = str(md_path.resolve())
    if key in seen:
        return
    seen.add(key)
    sources.append(_entry(name, md_path, "claude_md", load))
    sources.extend(_collect_imports(md_path.resolve(), seen, notes, allowed_base))


def _split_advertised(text: str) -> tuple[str, str]:
    """Split a SKILL/agent file into (advertised, body). ADVERTISED is the WHOLE
    frontmatter block seen at rest -- `---` delimiters plus every key (name:,
    description:, tools:, ...), not just the description value -- so the
    always-loaded entry is not under-reported and advertised+body covers the
    file. BODY is everything after (on-trigger); no description => all body."""
    fm = _FRONTMATTER_PATTERN.match(text)
    if not fm:
        return "", text
    advertised = fm.group(0) if _DESC_PATTERN.search(fm.group(1)) else ""
    return advertised, text[fm.end():]


def _add_advertised_source(sources, md_path: Path, kind: str, label: str) -> None:
    """Add a SKILL.md / agent file split into an always-loaded advertised (full
    frontmatter) entry and an on-trigger body entry; together they cover the
    whole file, so no scaffolding tokens silently vanish."""
    text = _read_text(md_path)
    if text is None:
        return
    advertised, body = _split_advertised(text)
    adv_tokens = count_tokens(advertised)[0] if advertised else 0
    body_tokens = count_tokens(body)[0] if body else 0
    base = md_path.parent.name if md_path.name == "SKILL.md" else md_path.stem
    if adv_tokens > 0:
        sources.append({
            "name": f"{label}:{base} (description)", "path": str(md_path),
            "category": f"{kind}_desc", "load": "always", "tokens": adv_tokens,
            "measured": True, "zone": _classify_zone(adv_tokens)[0],
        })
    sources.append({
        "name": f"{label}:{base} (body)", "path": str(md_path),
        "category": f"{kind}_body", "load": "on-trigger", "tokens": body_tokens,
        "measured": True, "zone": _classify_zone(body_tokens)[0],
    })


def _scan_claude_dir(sources, claude_dir: Path, label_prefix: str) -> None:
    """Scan a .claude directory for skills, agents, and commands."""
    skills_dir = claude_dir / "skills"
    if skills_dir.is_dir():
        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            _add_advertised_source(sources, skill_md, "skill", f"{label_prefix}skill")
    agents_dir = claude_dir / "agents"
    if agents_dir.is_dir():
        for agent_md in sorted(agents_dir.glob("*.md")):
            _add_advertised_source(sources, agent_md, "agent", f"{label_prefix}agent")
    commands_dir = claude_dir / "commands"
    if commands_dir.is_dir():
        for cmd_md in sorted(commands_dir.glob("*.md")):
            sources.append(
                _entry(f"{label_prefix}command:{cmd_md.stem}", cmd_md, "command", "on-demand")
            )


def _add_nested_claude_md(sources, project_root: Path, root_md: Path) -> None:
    """Find nested CLAUDE.md files in subdirs (conditional load). Prunes
    vendored/build/VCS trees so a dependency's CLAUDE.md does not inflate the
    pool, and skips entries whose resolved path escapes the project root (e.g. a
    symlink pointing outside) -- not in-project, and would crash relative_to."""
    root_key = str(root_md.resolve()) if root_md.is_file() else None
    root_resolved = project_root.resolve()
    for nested in sorted(project_root.rglob("CLAUDE.md")):
        if any(part in _PRUNED_DIRS for part in nested.parts):
            continue
        resolved = nested.resolve()
        if root_key is not None and str(resolved) == root_key:
            continue
        if resolved.parent == root_resolved:
            continue
        if not _within(resolved, root_resolved):
            continue
        rel = resolved.relative_to(root_resolved)
        sources.append(_entry(f"nested:{rel}", nested, "nested_claude_md", "conditional"))

# == Plugin enumeration =========================================

def _scan_plugins(sources, notes: list[str]) -> None:
    """Enumerate ENABLED plugin skills/agents from disk and count advertised
    descriptions (always-loaded); bodies count as on-trigger/on-demand."""
    settings = _read_json(Path.home() / ".claude" / "settings.json")
    installed = _read_json(Path.home() / ".claude" / "plugins" / "installed_plugins.json")
    if not isinstance(settings, dict) or not isinstance(installed, dict):
        return
    enabled = settings.get("enabledPlugins", {})
    if not isinstance(enabled, dict):
        return
    enabled_keys = {k for k, v in enabled.items() if v}
    plugins = installed.get("plugins", {})
    if not isinstance(plugins, dict):
        return
    for plugin_key, records in plugins.items():
        if plugin_key not in enabled_keys or not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue
            install_path = rec.get("installPath")
            if not install_path:
                continue
            base = Path(install_path)
            if not base.is_dir():
                notes.append(f"Enabled plugin path missing: {plugin_key}")
                continue
            short = plugin_key.split("@")[0]
            _scan_claude_dir(sources, base, f"plugin[{short}]")

# == MCP disk enumeration (honest heuristic) ====================

_MCP_NOTE: str = (
    "MCP tool schemas load at runtime; not measurable from disk. "
    "Run /project-scan interactively for a live estimate."
)


def _scan_mcp(project_root: Path) -> dict:
    """Enumerate MCP servers configured ON DISK only. Tool counts / schema
    sizes are NOT knowable from config, so estimated_tokens stays 0 with a
    clear note; the interactive SKILL layer supplies the live number."""
    server_names: set[str] = set()

    def _harvest(obj: object) -> None:
        if isinstance(obj, dict) and isinstance(obj.get("mcpServers"), dict):
            server_names.update(obj["mcpServers"].keys())

    _harvest(_read_json(project_root / ".mcp.json"))
    _harvest(_read_json(Path.home() / ".claude" / "settings.json"))
    claude_json = _read_json(Path.home() / ".claude.json")
    if isinstance(claude_json, dict):
        _harvest(claude_json)
        projects = claude_json.get("projects", {})
        if isinstance(projects, dict):
            _harvest(projects.get(str(project_root.resolve())))

    names = sorted(server_names)
    return {
        "method": "disk_enumeration", "servers_found": len(names),
        "server_names": names, "tokens_per_tool": _MCP_TOKENS_PER_TOOL,
        "estimated_tokens": 0, "note": _MCP_NOTE,
    }

# == Top-level scan =============================================

def scan_project(project_root: str, include_global: bool = True, include_mcp: bool = True) -> dict:
    """
    Inventory every always-loaded context source for `project_root`, plus the
    on-demand pool, and return the resting-context manifest. READ-ONLY.
    """
    root = Path(project_root).resolve()
    sources: list[dict] = []
    notes: list[str] = []
    seen: set[str] = set()

    # Project-level always-loaded CLAUDE.md + imports.
    # Project @imports are contained to the project tree (untrusted content).
    _add_claude_md_chain(
        sources, seen, notes, root / "CLAUDE.md", "CLAUDE.md", "always", root
    )
    _add_claude_md_chain(
        sources, seen, notes, root / "CLAUDE.local.md", "CLAUDE.local.md", "always", root
    )

    # User-global CLAUDE.md + imports. Its @import chain is contained to
    # ~/.claude, NOT all of $HOME.
    if include_global:
        claude_home = (Path.home() / ".claude").resolve()
        _add_claude_md_chain(
            sources, seen, notes,
            claude_home / "CLAUDE.md", "~/.claude/CLAUDE.md", "always", claude_home,
        )

    # Nested (conditional) CLAUDE.md in subdirs.
    _add_nested_claude_md(sources, root, root / "CLAUDE.md")

    # Project .claude skills / agents / commands.
    _scan_claude_dir(sources, root / ".claude", "")

    # Enabled plugins.
    if include_global:
        _scan_plugins(sources, notes)

    # MCP (estimated, disk enumeration only).
    if include_mcp:
        mcp = _scan_mcp(root)
        if mcp["estimated_tokens"] > 0:
            sources.append({
                "name": f"MCP tool schemas ({mcp['servers_found']} server(s))",
                "path": "(runtime)", "category": "mcp", "load": "always",
                "tokens": mcp["estimated_tokens"], "measured": False,
                "zone": _classify_zone(mcp["estimated_tokens"])[0],
            })
    else:
        mcp = {
            "method": "skipped", "servers_found": 0, "server_names": [],
            "tokens_per_tool": _MCP_TOKENS_PER_TOOL, "estimated_tokens": 0,
            "note": "MCP scan skipped (--no-mcp).",
        }

    sources.sort(key=lambda s: s["tokens"], reverse=True)

    always = [s for s in sources if s["load"] == "always"]
    resting_baseline = sum(s["tokens"] for s in always)
    measured = sum(s["tokens"] for s in always if s["measured"])
    estimated = sum(s["tokens"] for s in always if not s["measured"])
    on_demand = sum(s["tokens"] for s in sources if s["load"] != "always")
    resting_zone, resting_action = _classify_zone(resting_baseline)

    if not always:
        notes.append("No always-loaded sources found (no CLAUDE.md / config).")

    return {
        "project_root": str(root),
        "resting_baseline_tokens": resting_baseline,
        "measured_tokens": measured,
        "estimated_tokens": estimated,
        "resting_zone": resting_zone,
        "resting_action": resting_action,
        "on_demand_pool_tokens": on_demand,
        "sources": sources,
        "mcp": mcp,
        "method": "scan_project",
        "notes": notes,
    }

# == Report formatter ===========================================
_ZONE_MARKERS: dict[str, str] = {
    "GREEN": "[OK]", "YELLOW": "[!!]", "ORANGE": "[##]",
    "RED": "[XX]", "CRITICAL": "[!!XX!!]",
}


def format_report(manifest: dict) -> str:
    """Format the scan manifest as a human-readable terminal report."""
    out: list[str] = []
    zm = _ZONE_MARKERS
    rz = manifest["resting_zone"]

    out.append("=" * 72)
    out.append("  PROJECT RESTING-CONTEXT SCAN")
    out.append("=" * 72)
    out.append("")
    out.append(f"  Project:   {manifest['project_root']}")
    out.append(f"  Method:    {manifest['method']} (READ-ONLY)")
    out.append("")
    out.append(f"  RESTING BASELINE: {manifest['resting_baseline_tokens']} tokens")
    out.append(f"  Zone:      {zm.get(rz, '   ')} {rz}")
    out.append(f"  Action:    {manifest['resting_action']}")
    out.append("")
    out.append(
        f"  Measured:  {manifest['measured_tokens']} tok   "
        f"Estimated: {manifest['estimated_tokens']} tok ({_EST_MARK})"
    )
    out.append(f"  On-demand pool (not at rest): {manifest['on_demand_pool_tokens']} tokens")

    out.append("")
    out.append("-" * 72)
    out.append("  SOURCE BREAKDOWN (largest first)")
    out.append("-" * 72)
    for s in manifest["sources"]:
        mark = "    " if s["measured"] else _EST_MARK
        z = zm.get(s["zone"], "   ")
        out.append(
            f"  {s['tokens']:>5} tok  {s['load']:<11} {mark:<5} {z:<10} {s['name']}"
        )

    mcp = manifest["mcp"]
    out.append("")
    out.append("-" * 72)
    out.append("  MCP (estimated, runtime-only)")
    out.append("-" * 72)
    out.append(
        f"  Servers found on disk: {mcp['servers_found']}"
        + (f" -> {', '.join(mcp['server_names'])}" if mcp["server_names"] else "")
    )
    out.append(f"  Heuristic: ~{mcp['tokens_per_tool']} tok/tool (estimated)")
    out.append(f"  Note: {mcp['note']}")

    if manifest["notes"]:
        out.append("")
        out.append("-" * 72)
        out.append("  NOTES")
        out.append("-" * 72)
        for n in manifest["notes"]:
            out.append(f"  - {n}")

    out.append("=" * 72)
    return "\n".join(out)

# == Entry point ================================================

def main() -> None:
    """CLI entry point."""
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        sys.stdout.write(
            "Usage: python3 scan_project.py [PROJECT_ROOT] "
            "[--json] [--no-global] [--no-mcp]\n\n"
            "  PROJECT_ROOT   defaults to current working directory\n"
            "  --json         print the raw manifest as JSON\n"
            "  --no-global    skip user-global ~/.claude sources and plugins\n"
            "  --no-mcp       skip MCP server enumeration\n"
        )
        sys.exit(0)

    as_json = "--json" in args
    include_global = "--no-global" not in args
    include_mcp = "--no-mcp" not in args
    positional = [a for a in args if not a.startswith("--")]
    project_root = positional[0] if positional else str(Path.cwd())

    manifest = scan_project(project_root, include_global=include_global, include_mcp=include_mcp)

    if as_json:
        sys.stdout.write(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        sys.stdout.write(format_report(manifest))
    sys.stdout.write("\n")

if __name__ == "__main__":
    main()

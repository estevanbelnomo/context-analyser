# /project-scan: Resting Baseline

Read-only, stateless. Inventories EVERY token loaded at rest --
before the user types -- the baseline on the context-rot curve.
CLAUDE.md is one slice.

## Always vs on-demand

Always (in baseline): root CLAUDE.md + @imports (recursive,
cycle-safe, depth 5); CLAUDE.local.md; ~/.claude/CLAUDE.md +
@imports; SKILL.md / agent FRONTMATTER (the advert); enabled plugin
descriptions; MCP schemas (estimated).

On-demand (NOT at rest): skill/agent bodies; commands; nested subdir
CLAUDE.md (conditional).

## Scope + containment

Only WHOLE-LINE @imports count; inline @mentions are out of scope.
@import targets stay inside their tree (project root, or ~/.claude),
so untrusted content can't reach arbitrary $HOME files; escapes are
noted, never read.

## MCP hybrid

Schemas aren't on disk for hosted servers. The script enumerates
configured servers (count + names, estimated = 0). YOU refine
in-session: count loaded tools, add ~300 tok each, label
"~estimated" outside measured.

## Read + act

RESTING BASELINE + zone is the headline (zones reuse
context-rot-thresholds.md). Then the measured-vs-estimated split,
the breakdown table, MCP line, on-demand pool.

Baseline > 500? The biggest always-loaded entries are the levers:
route CLAUDE.md bulk through Restructure -> Compress -> Tier; trim
descriptions; drop unused plugins/MCP. Run `scan_project.py`.

# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-06-19

### Added

- `/project-scan` command: a read-only, stateless full-project context scan that reports the entire resting-context baseline -- not just CLAUDE.md, but every always-loaded source -- and its context-rot zone, alongside a separate on-demand pool.
- `scripts/scan_project.py`: a read-only full-project resting-context-budget analyser (stdlib only). It resolves CLAUDE.md `@imports` recursively (cycle-safe, depth-capped), inventories user-global memory (`~/.claude/CLAUDE.md` and its imports), CLAUDE.local.md, nested subdirectory CLAUDE.md files, and skill/agent/command and enabled-plugin descriptions, and produces an honest MCP hybrid estimate (enumerates configured MCP servers from disk and labels tool-schema tokens as estimated, since they are not measurable from disk). Reuses `count_tokens` for the tokenizer and zone thresholds (single source of truth).
- Tests (`tests/test_scan_project.py`) with a sample-project fixture tree, plus a `references/project-scan.md` guidance document.

## [1.1.1] - 2026-06-19

### Fixed

- Phase numbering now matches execution order across SKILL.md, references, and README: Restructure = Phase 1, Compress = Phase 2, Tier = Phase 3 (previously the labels called Compress "phase 1" and Restructure "phase 2", contradicting the documented Restructure -> Compress -> Tier order). Gate numbers in SKILL.md realigned to execution order.
- SKILL.md compressed back under 500 tokens (GREEN) by the bundled counter, restoring self-compliance with the project's own token budget (was ~641, YELLOW).
- Test gate made honest: documentation now points at the stdlib standalone runners (python3 tests/test_count_tokens.py / test_boundary_check.py) instead of pytest, and the test "_assert" helper now raises on failure so a failing assertion can no longer be reported as a pass.
- Plugin version metadata synced to 1.1.1 across plugin.json, package.json, and marketplace.json (were stuck at 1.0.0).
- Corrected README install instructions: the plugin install command now uses the registered marketplace name (`context-analyser@context-analyser`, not `@estevanbelnomo/context-analyser`), and the manual-install section now symlinks/copies the `skills/context-analyser` subdirectory instead of cloning the whole repo into `.claude/skills/` (which nested `SKILL.md` two levels too deep and was undiscoverable).

### Changed

- Documentation standardized on "python3" for all command-line invocations.

## [1.1.0] - 2026-04-14

### Added

- Claude Code plugin structure (.claude-plugin/plugin.json, marketplace.json, package.json)
- Plugin install via `/plugin marketplace add estevanbelnomo/context-analyser`
- Phase projection table at Gate 0 showing estimated tokens per phase
- Cumulative stepped path when no single phase reaches GREEN
- Auto/Manual/Stop choice at Gate 0
- Project CLAUDE.md with contribution rules and token budgets
- layered-architecture-detail.md (examples and anti-patterns, loaded JIT)

### Changed

- Restructured as plugin: skill files moved to `skills/context-analyser/`
- Pipeline order fixed to Restructure -> Compress -> Tier (was Compress first)
- Token counter now mandatory before any report (ALWAYS run, not optional)
- Projections use actual counter JSON, not manual estimates
- SKILL.md description compressed (246 -> 143 tokens preamble)
- layered-architecture.md split: core model (493 tok) + detail file (503 tok)
- tiering.md trimmed (655 -> 583 tokens)
- boundary-score.md trimmed (640 -> 445 tokens)
- README.md updated with plugin install instructions and new paths

## [1.0.0] - 2026-04-13

### Added

- Four-phase escalating pipeline: Audit, Compress, Restructure, Tier
- Token counting via Anthropic API (exact) with pure-stdlib Python fallback (~94%)
- Zone classification system (GREEN/YELLOW/ORANGE/RED/CRITICAL) based on Chroma context rot research
- Per-section token breakdown with tier recommendations
- Boundary score system: six scope governance rules (Scope Containment, Confirmation Gates, Semantic Boundary, File Tree Containment, Statelessness, Network Isolation)
- Semantic preservation checker for compression phase (keyword Jaccard, negation detection, imperative polarity)
- AST security scanner (self_test.py) verifying zero external dependencies and no dangerous builtins
- Input path validation with symlink escape protection
- Five reference documents: compression, restructuring, layered architecture, tiering, context rot thresholds
- 89 tests (57 count_tokens + 32 boundary_check)

### Security

- Zero external Python dependencies (stdlib only)
- Python never makes network calls (only bash curl for API)
- No eval, exec, pickle, subprocess, importlib
- All regex patterns compiled at module level (no dynamic patterns)
- Path validation blocks null bytes, traversal, and symlink escapes

## [Unreleased] - V2 Backlog

### Planned

- Session-start hook for automatic CLAUDE.md audit (Approach 3 enhancement)
- Keyword-based domain detection in _recommend_tier (currently size-based only)
- npm plugin distribution for `claude install` workflow
- Diff tracking between audits (requires opt-out of STATELESS rule)
- Multi-file directory scanning (audit entire .claude/ tree)
- Custom zone thresholds (per-model tuning)
- Per-edit granular accept/reject in compression phase
- `/project-scan`: when a project root sits entirely outside `_validate_path`'s allowed roots (cwd / home / /tmp / /mnt), files are read as 0 tokens *silently* (the validator rejects them) instead of emitting a note. The baseline then under-reports without explanation. Surface a clear "source outside allowed roots — not measured" note per affected source, or warn once up front. (Found 2026-06-19 while verifying v1.2.0; deferred — real project roots are covered by the existing allowed roots.)

### Known Test Gaps (see tests/KNOWN_TEST_GAPS.md)

- Unicode/non-ASCII content in CLAUDE.md files
- YAML frontmatter parsing
- Headers inside fenced code blocks
- Empty sections (0-token bodies)
- Very large files (30+ sections) against bash counter

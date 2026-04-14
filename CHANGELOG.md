# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

### Known Test Gaps (see tests/KNOWN_TEST_GAPS.md)

- Unicode/non-ASCII content in CLAUDE.md files
- YAML frontmatter parsing
- Headers inside fenced code blocks
- Empty sections (0-token bodies)
- Very large files (30+ sections) against bash counter

# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

---
name: context-analyser
description: >
  Audit and optimise CLAUDE.md for token efficiency and context rot. Trigger on
  /audit, /project-scan, /compress, /restructure, /tier, /context-check, or any
  mention of token budget, instruction bloat, or CLAUDE.md optimisation. Also
  when Claude forgets/ignores instructions or degrades over long sessions.
---

# Context Analyser

Audit/scan are read-only entries, not phases. After audit pick Auto or
Manual. Phase order is ALWAYS Restructure, Compress, Tier.

## Commands
/audit          read-only token audit
/project-scan   read-only whole-project context scan
/restructure P1, /compress P2, /tier P3 (run in that order)
/context-check  full pipeline

## Token Counter
ALWAYS run before reports/projections: count_tokens.sh with
ANTHROPIC_API_KEY, else count_tokens.py. Use --json, never estimates.
/project-scan runs scan_project.py. MCP estimate (interactive): count
live tools, +~300 tok each, label estimated.

## Phase Routing
Load ONLY the active phase reference (references/):
/project-scan project-scan. P1 restructuring, layered-architecture
(ex layered-architecture-detail). P2 compression. P3 tiering.
context-rot-thresholds at audit; boundary-score before write phases.

## Gates
Never write/execute before confirming the gate output.
G0 audit: projections; pick Auto/Manual. G1 restructure: file tree.
G2 compress: diff. G3 tier: assignments.

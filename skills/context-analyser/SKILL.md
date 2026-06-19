---
name: context-analyser
description: >
  Audit and optimise CLAUDE.md for token efficiency and context rot. Trigger
  on: /audit, /compress, /restructure, /tier, /context-check, or any mention
  of token budget, context rot, instruction bloat, CLAUDE.md optimisation.
  Also trigger when user reports Claude "forgetting" or "ignoring" instructions,
  or instruction quality degrading over long sessions.
---

# Context Analyser

Audit is a read-only entry, not a phase. After audit, pick Auto or
Manual. Order is ALWAYS Restructure, Compress, Tier.

## Commands
/audit          read-only token audit
/restructure    layered architecture, phase 1
/compress       rewrite concisely, phase 2
/tier           split into tiers, phase 3
/context-check  full pipeline

## Token Counter
ALWAYS run the counter before any report or projection.
With ANTHROPIC_API_KEY use count_tokens.sh, else python3 count_tokens.py.
Use --json counts, never estimates.

## Phase Routing
Load ONLY the active phase reference (references/):
P1 restructuring, layered-architecture; ex layered-architecture-detail.
P2 compression. P3 tiering.
context-rot-thresholds during audit; boundary-score before write phases.

## Gates
Never write or execute before confirming the gate's output.
G0 after audit: projections, order Restructure, Compress, Tier; pick Auto or Manual.
G1 after restructure: file tree.
G2 after compress: diff.
G3 after tier: assignments.

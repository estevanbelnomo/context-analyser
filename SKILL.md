---
name: context-analyser
description: >
  Analyse and optimise CLAUDE.md files for token efficiency and context rot
  mitigation. Use this skill whenever the user mentions CLAUDE.md optimisation,
  token budget, context rot, instruction bloat, context length, or asks to
  audit, compress, restructure, or tier their CLAUDE.md or project instruction
  files. Also trigger on /audit, /compress, /restructure, /tier commands, or
  when a user reports that Claude Code is "forgetting" or "ignoring" their
  instructions. This skill should be used even if the user does not explicitly
  mention "context rot" -- any complaint about instruction quality degrading
  over long sessions is a trigger.
---

# Context Analyser

Audits CLAUDE.md for token efficiency via four-step escalating pipeline:
Audit -> Compress -> Restructure -> Tier. Each step runs only if the
previous did not reach GREEN (< 500 tokens).

## Commands
/audit           Analyse token usage. Read-only, always safe.
/compress        Rewrite instructions concisely (phase 1).
/restructure     Apply layered architecture (phase 2).
/tier            Split into tiered files (phase 3).
/context-check   Full pipeline: audit then escalate as needed.

## Token Counter
If ANTHROPIC_API_KEY set: scripts/count_tokens.sh <file>
Otherwise: python scripts/count_tokens.py <file>
Both output same JSON schema. --json for machine-readable output.

## Phase Routing
After audit, load ONLY the reference for the current phase:
Phase 1: references/compression.md
Phase 2: references/restructuring.md + references/layered-architecture.md
Phase 3: references/tiering.md
Thresholds: references/context-rot-thresholds.md (load during audit)
Boundaries: references/boundary-score.md (load before write phases 1/2/3)

## Gates
G0: After audit. Show report. User chooses auto or manual.
G1: After compression. Show diff. Confirm before writing.
G2: After restructure. Show file tree. Confirm before creating.
G3: After tiering. Show assignments. Confirm before executing.
Never write any file without the relevant gate confirmation.

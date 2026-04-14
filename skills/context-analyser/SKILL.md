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

Audits CLAUDE.md for token efficiency via four-phase pipeline:
Audit -> Restructure -> Compress -> Tier. After audit, user
chooses Auto or Manual. Step order is ALWAYS 1-2-3.

## Commands
/audit           Token audit. Read-only.
/compress        Rewrite concisely (phase 1).
/restructure     Layered architecture (phase 2).
/tier            Split into tiered files (phase 3).
/context-check   Full pipeline.

## Token Counter
ALWAYS run the counter before generating any report or projection.
If ANTHROPIC_API_KEY set: scripts/count_tokens.sh <file>
Otherwise: python scripts/count_tokens.py <file>
Use --json. Use actual token counts from JSON, not estimates.

## Phase Routing
After audit, load ONLY the current phase reference:
Phase 1: references/compression.md
Phase 2: references/restructuring.md + references/layered-architecture.md
         (examples: references/layered-architecture-detail.md)
Phase 3: references/tiering.md
Thresholds: references/context-rot-thresholds.md (during audit)
Boundaries: references/boundary-score.md (before write phases)

## Gates
G0: After audit. Show projections. Order: Restructure->Compress->Tier. User chooses Auto/Manual.
G1: After compression. Show diff. Confirm before writing.
G2: After restructure. Show file tree. Confirm before creating.
G3: After tiering. Show assignments. Confirm before executing.
Never write without gate confirmation.

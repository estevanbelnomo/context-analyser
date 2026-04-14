# Boundary Score: Scope Governance

Pre-flight check before every write. Score 0-100. Any boundary at 0 = hard block.

## Boundaries

**A: Scope (30 pts)** -- Only instruction files (CLAUDE.md, .claude/*.md,
confirmed docs/*.md). Not source code, config, or .git/.

**B: Gates (20 pts)** -- G0-G3 always fire. Never auto-apply writes.

**C: Semantic (20 pts)** -- Editor, not author. Compress/reorder/classify OK.
No adding, removing, or changing instruction meaning.
Check: Jaccard >=0.55, negations preserved, polarity unchanged.

**E: File Tree (15 pts)** -- Writes only to CLAUDE.md, .claude/*.md,
confirmed docs/*.md.

**F: Stateless (10 pts)** -- No cross-session state or cache files.

**G: Network (5 pts)** -- Python never touches network. Only bash curl.

## Thresholds

80-100: Proceed. 50-79: Ask user. 0-49: Block.
Any single boundary at 0 = VIOLATION regardless of total.

## Pre-Flight Steps

1. Classify target files (A). 2. Verify gate present (B).
3. Classify semantic op (C). 4. Check write targets (E).
5. Confirm no prior state (F). 6. Confirm no Python network (G).

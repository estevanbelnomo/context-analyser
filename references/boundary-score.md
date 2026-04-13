# Boundary Score: Scope Governance

Pre-flight check before every write. Score 0-100. Any boundary at 0 = hard block.

## Boundaries

**A: Scope Containment (30 pts)** -- Only instruction files.
In scope: CLAUDE.md, .claude/*.md, docs/*.md (confirmed as instruction).
Out: *.py, *.rs, *.ts, *.toml, *.yaml, *.json, *.env, README.md, .git/.
Edge case (docs/): ask user to confirm instruction vs documentation.

**B: Confirmation Gates (20 pts)** -- Never auto-apply.
G0: Audit (read-only). G1: Compress (show diff). G2: Restructure (show tree).
G3: Tier (show assignments). Gates always fire, even with "auto-apply" permission.

**C: Semantic Boundary (20 pts)** -- Editor, not author.
Permitted: compress, deduplicate (with confirm), reorder, classify.
Blocked: add instructions, remove without equivalent, change conditions,
strengthen/weaken, infer unstated rules.
Check: keyword Jaccard >= 0.55, negations preserved, polarity unchanged.

**E: File Tree Containment (15 pts)** -- Writes only to CLAUDE.md,
.claude/*.md, docs/*.md (confirmed). May create .claude/ and .claude/archive/.

**F: Statelessness (10 pts)** -- No cross-session state. No cache files.
Intra-session backups are temporary, cleaned up at pipeline end.

**G: Network Isolation (5 pts)** -- Python never touches network.
Only count_tokens.sh calls Anthropic API.

## Thresholds

80-100: Proceed. 50-79: Ask user. 0-49: Block.
Any single boundary at 0 = VIOLATION regardless of total.

## Pre-Flight Steps

1. Classify target files (A). 2. Verify gate present (B).
3. Classify semantic op (C). 4. Check write targets (E).
5. Confirm no prior state (F). 6. Confirm no Python network (G).

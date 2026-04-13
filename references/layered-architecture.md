# Layered Context Management Architecture

Maps production RAG patterns to Claude Code primitives.

## The Five Layers

| # | Production Equivalent | Claude Code Primitive | Budget         |
|---|----------------------|----------------------|----------------|
| 1 | Prompt cache         | CLAUDE.md core       | < 500 (always) |
| 2 | Agentic tools        | Skill files          | 0 at rest, <800|
| 3 | Hybrid retrieval     | File reads + grep    | Variable (JIT) |
| 4 | Reranker             | Priority rules       | Built into L1  |
| 5 | Compression          | Compaction rules     | ~100 in core   |

## Layer 1: Static Core

Always loaded. < 500 tokens. Contains: project identity, universal rules
(5-10 max), skill/command INDEX, compaction triggers.
Never contains: API refs, full examples, domain knowledge, history.

## Layer 2: On-Demand Skills

0 at rest, < 800 each when active. .claude/*.md files auto-loaded
when trigger keywords match. If > 800, split or use Layer 3 refs.

## Layer 3: JIT Reference

0 at rest. /commands or conditional reads. Include task description
repetition in command preambles (survives rot in long sessions).

## Layer 4: Runtime File Reads

Variable, loaded and discarded per task. CLAUDE.md says WHERE and
WHEN to read, never inlines content. Discard instructions in Layer 1.

## Layer 5: Compaction Rules

~100 tokens in core, saves thousands. Proactive rules:
- "Summarise outcome in 1-2 lines after completing task."
- "Don't keep file contents. Reference by path only."
- "At 40+ messages, write PROGRESS.md before continuing."
Fire BEFORE rot threshold, never after.

## Token Budget Flow

Idle: ~500. Skill loaded: ~1,300. Skill + file: ~2,800 (temp).
After compaction: ~500. Context is a QUEUE, not a STACK.

## Anti-Patterns

| Problem                | Fix                         |
|------------------------|-----------------------------|
| Monolithic CLAUDE.md   | L1 caps at 500              |
| Inline API docs        | L3: read when needed        |
| All rules in one file  | L2: domain isolation        |
| No compaction strategy | L5: proactive rules         |
| Examples with rules    | L3: /examples loads JIT     |
| File contents persist  | L5: path-only after use     |

## Layout

```
CLAUDE.md                  <- T0 (< 500)
.claude/database.md        <- T1 (< 800)
.claude/ui.md              <- T1
.claude/archive/adr-001.md <- T3
docs/migration-checklist.md <- T2
```

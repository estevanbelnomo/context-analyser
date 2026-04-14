# Layered Context Architecture

Maps RAG patterns to Claude Code primitives.

## Five Layers

L1 Static Core: CLAUDE.md, <500 tok, always loaded.
L2 On-Demand Skills: .claude/*.md, <800 each, auto-loaded on trigger.
L3 JIT Reference: /commands or conditional reads, 0 at rest.
L4 Runtime Reads: file reads per task, discarded after use.
L5 Compaction: ~100 tok in core, proactive summarisation rules.

## L1: Static Core

Contains: identity, universal rules (5-10), skill INDEX, compaction triggers.
Never contains: API refs, examples, domain knowledge, history.

## L2: On-Demand Skills

.claude/*.md auto-loaded when trigger keywords match.
If >800 tok, split or move detail to L3 references.

## L3-L4: Reference & Reads

L3: /commands or conditional reads. 0 at rest.
L4: file reads loaded and discarded per task. CLAUDE.md says WHERE
and WHEN to read, never inlines content.

## L5: Compaction Rules

~100 tok in core, saves thousands:
- "Summarise outcome in 1-2 lines after task."
- "Reference by path only, don't keep file contents."
- "At 40+ messages, write PROGRESS.md."
Fire BEFORE rot threshold, never after.

## Budget Flow

Idle: ~500. +Skill: ~1,300. +File: ~2,800 (temp). After compaction: ~500.
Context is a QUEUE, not a STACK.

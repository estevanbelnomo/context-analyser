# Phase 2: Restructure

Apply 5-layer architecture. Move domain content out of core.
See references/layered-architecture.md for the full model.

## Classification

**Layer 1 (Core):** Identity, universal rules, routing index, commands,
session management. Stays in CLAUDE.md.

**Layer 2 (Skill):** Domain-specific rules. Moves to .claude/<domain>.md.

**Layer 3 (Reference):** Checklists, templates, specs. Moves to docs/.

Test: "Applies to EVERY task?" -> L1. "Specific domain?" -> L2.
"Checklist/template/spec?" -> L3.

## Core Template (< 500 tokens)

```
## Identity (2-3 lines)
## Universal Rules (5-10 max)
## Context Loading (routing index)
## Commands
## Session Management
```

## Skill File Template (< 800 tokens each)

```
# [Domain]
## Rules
## Patterns
## Reference Files (read when needed)
```

Trigger keywords: 3-6 per file, nouns, disjoint across files.

## Workflow

1. Classify sections into Layer 1/2/3.
2. Generate new CLAUDE.md core (L1 + routing index).
3. Generate .claude/*.md stubs (L2).
4. Generate reference stubs (L3).
5. Verify: core < 500, skill files < 800.
6. GATE 2: [Apply] [Modify] [Stop].
7. Write files (FILE_TREE_CONTAINMENT check each).
8. GREEN? Done. Otherwise recommend Phase 3.

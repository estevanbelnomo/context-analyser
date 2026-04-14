# Layered Architecture: Examples & Anti-Patterns

Supplementary to layered-architecture.md. Load when examples are needed.

## Anti-Patterns

- Monolithic CLAUDE.md -> L1 caps at 500
- Inline API docs -> L3: read when needed
- All rules in one file -> L2: domain isolation
- No compaction -> L5: proactive rules
- Examples with rules -> L3: /examples JIT
- File contents persist -> L5: path-only after use

## Example Layout

```
CLAUDE.md                  <- T0 (< 500)
.claude/database.md        <- T1 (< 800)
.claude/ui.md              <- T1
.claude/archive/adr-001.md <- T3
docs/migration-checklist.md <- T2
```

## Example Core CLAUDE.md (SP-DB Project)

```markdown
# SP-DB
SQLite analytics dashboard. Python + Textual TUI.

## Rules
- Type hints on all public functions.
- SQL: parameterised queries only.
- Tests: pytest, no mocks for DB layer.

## Context Loading
Database: .claude/database.md (trigger: sql, migration, schema)
UI: .claude/ui.md (trigger: component, widget, screen)
Export: .claude/export.md (trigger: csv, pdf, report)

## Commands
/migrate   Run pending migrations
/test      pytest tests/ -v
```

# TestProject
Rust/Tauri v2. Desktop stock query tool.

## Rules
- Parameterised SQL only. No string interpolation.
- Use thiserror (lib) / anyhow (bin). No unwrap() in production.
- All public functions require tests.
- British English in user-facing strings.

## Context Loading
When working on database/SQL, load .claude/database.md
When working on UI/components, load .claude/ui.md

## Commands
/audit    Analyse CLAUDE.md token usage
/schema   Load current database ERD

## Session Management
- After completing a task, summarise outcome in 1-2 lines.
- Do not retain file contents in context. Reference by path.

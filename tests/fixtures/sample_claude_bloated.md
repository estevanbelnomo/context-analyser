# TestProject: SimPRO Database Tool
Rust/Tauri v2/Leptos/PostgreSQL. Desktop application for stock management queries and exports.

## Universal Rules
- You should always make sure to use parameterised queries when writing SQL. Never use string interpolation for SQL queries as this could lead to SQL injection vulnerabilities.
- It is important that you use thiserror for library code and anyhow for binary code. Please note that you should never use unwrap() in production code. Instead, use the ? operator or provide explicit error handling with meaningful error messages.
- All public functions require comprehensive test coverage. Tests should cover both the happy path and error cases.
- Please use British English in all user-facing strings and documentation.
- When writing commit messages, always follow the conventional commits format: type(scope): description.

## Database Conventions
- Always create reversible migrations with both up and down scripts.
- Migration file naming format should be YYYYMMDD_HHMMSS_description.sql.
- Before generating any migration SQL, you should read the migration checklist at docs/migration-checklist.md.
- Test all migrations against a throwaway database before applying them to the development database.
- Use Common Table Expressions (CTEs) for complex queries. Do not use nested subqueries beyond 2 levels of nesting.
- All JOIN operations must specify the join type explicitly (INNER JOIN, LEFT JOIN, etc.). Never use implicit joins.
- You should create an index for any column that is used in a WHERE clause or JOIN condition if the table has more than 10,000 rows.
- Primary keys should always be id BIGSERIAL.
- All tables must have created_at TIMESTAMPTZ DEFAULT now() and updated_at TIMESTAMPTZ columns.
- For soft deletes, use deleted_at TIMESTAMPTZ NULL.
- All foreign keys must specify ON DELETE behaviour (CASCADE, SET NULL, RESTRICT, etc.).

## UI Component Patterns
- All Leptos components should follow the signal-based reactivity pattern.
- Use the component macro (#[component]) for all public components.
- Props must implement Clone and PartialEq for memoisation.
- Style with Tailwind utility classes. No custom CSS unless absolutely necessary.
- All user-facing text must go through the i18n system.
- Error states should always show a user-friendly message, not raw error text.
- Loading states are required for any async operation.

## Export Format Specification
- The primary export format is XLSX for Xero integration.
- Column headers must match the Xero import template exactly. See docs/xero-export-spec.md for the full mapping.
- Date format in exports: YYYY-MM-DD (ISO 8601).
- Currency values must be formatted with 2 decimal places, no currency symbol.
- The export should include a summary row at the bottom with totals for all numeric columns.
- Maximum export size is 50,000 rows. For larger datasets, split into multiple files.

## Testing Rules
- Use the test fixtures in tests/fixtures/ directory. Do not create ad-hoc test data.
- Integration tests must use a real PostgreSQL database, not mocks.
- Test database is automatically provisioned by the test harness.
- Snapshot tests for all UI components.
- Performance tests required for any query touching tables with more than 100K rows.

## Deployment
- Tauri builds must be signed with the project signing key.
- CI pipeline runs on every push to main.
- Release builds use the release profile with optimisations enabled.
- The application auto-updates via Tauri's built-in updater.
- Environment-specific configuration goes in config/{env}.toml.

## Context Management
- After completing a task, summarise the outcome in 1-2 lines and discard intermediate reasoning.
- Do not keep file contents in context after processing. Reference files by path only.
- When conversation exceeds 50 messages, create a PROGRESS.md with current state before continuing.
- When reading reference files, extract only what is needed for the current task.

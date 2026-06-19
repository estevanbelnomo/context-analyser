# Sample Project

This is the root CLAUDE.md for the scanner test fixture. It carries a small
amount of prose so the token count is non-trivial but well inside the GREEN
zone, plus a single @import directive that the scanner must resolve.

## Rules
- Use stdlib only.
- Keep instructions short and actionable.
- Prefer explicit paths over implicit discovery.

@imported.md

The text above the import and below it should both be counted as part of the
root file. The imported file is a separate manifest entry in the import
category, inheriting the always-load timing of its parent.

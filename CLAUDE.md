# context-analyser

Claude Code skill for CLAUDE.md token optimisation.

## Rules
- Python stdlib only. No external imports. No eval/exec/pickle/subprocess.
- Only count_tokens.sh touches the network (bash + curl).
- Regex compiled at module level. Paths validated via _validate_path.

## Budgets
- SKILL.md body: <500 tok. References: <600 tok each.
- Max concurrent: SKILL.md + one reference <1,700 tok.

## Testing
- `python skills/context-analyser/scripts/self_test.py` (security scan)
- `python -m pytest tests/ -v` (all tests must pass)
- `python skills/context-analyser/scripts/count_tokens.py skills/context-analyser/SKILL.md` after SKILL.md edits

## Boundaries
- Writes only to .claude/, CLAUDE.md, docs/*.md. No source code.
- No state between sessions. No files outside instruction tree.

## Contributing
- Python files <500 lines. New imports need self_test.py update.
- Update CHANGELOG.md for user-visible changes.

# Known Test Gaps

Identified during code review (2026-04-13). To be addressed in a dedicated
test hardening pass. None are blocking for V1.

## Gap 1: Unicode Content
**Risk:** Pre-tokenizer may miscount non-ASCII CLAUDE.md files (CJK, Cyrillic, emoji).
**Test needed:** Create a fixture with mixed Unicode content, count tokens,
verify against API exact count. Acceptable error margin: +/- 10%.

## Gap 2: YAML Frontmatter
**Risk:** Section parser may treat `---` frontmatter delimiters as content and
count frontmatter as a section body rather than metadata.
**Test needed:** Fixture with `---` YAML frontmatter (name, description fields).
Verify frontmatter is either excluded from section bodies or correctly isolated
as a "(preamble)" section.

## Gap 3: Headers Inside Code Blocks
**Risk:** Markdown headers (`# ...`) inside fenced code blocks (```) are parsed
as section boundaries when they should be treated as code content.
**Test needed:** Fixture with a code block containing `# comment` and `## header`
lines. Verify they are NOT treated as section splits.

## Gap 4: Empty Sections
**Risk:** A header immediately followed by another header produces a section with
empty body. Token count is 0. Tier logic at 0 tokens is untested.
**Test needed:** Fixture with consecutive headers. Verify 0-token sections are
classified as T0 and do not cause division-by-zero in percentage calculations.

## Gap 5: Very Large Files (30+ Sections)
**Risk:** count_tokens.sh makes N+1 API calls (1 total + N per-section). At 30+
sections this may hit rate limits or produce slow/unreliable results.
**Test needed:** Generate a synthetic 35-section CLAUDE.md. Run bash counter.
Verify all sections are counted and no API errors occur. This test requires
ANTHROPIC_API_KEY and network access.

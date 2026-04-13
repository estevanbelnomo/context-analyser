# context-analyser

A Claude Code skill that audits and optimises CLAUDE.md files for token efficiency and context rot mitigation.

Context rot is the measurable degradation of LLM output quality as input token count increases -- even when the context window is far from full. Research by [Chroma (July 2025)](https://research.trychroma.com/context-rot) tested 18 frontier models and found that every one degrades as input length grows. This skill helps you keep your CLAUDE.md lean enough that Claude Code actually follows your instructions.

## What It Does

Runs a four-phase escalating pipeline on your CLAUDE.md:

1. **Audit** -- counts tokens per section, classifies into zones (GREEN/YELLOW/ORANGE/RED/CRITICAL), recommends tier assignments
2. **Compress** -- rewrites instructions more concisely while preserving meaning (30-50% reduction typical)
3. **Restructure** -- applies a layered architecture: lean core CLAUDE.md + domain skill files loaded on demand
4. **Tier** -- decomposes remaining content into Tier 0 (always loaded), Tier 1 (auto-loaded by domain), Tier 2 (reference, JIT), Tier 3 (archive)

Each phase only runs if the previous one didn't bring the file into the GREEN zone (< 500 tokens). You can stop at any gate.

## Zone Thresholds

| Zone     | Tokens         | What Happens                                  |
|----------|----------------|-----------------------------------------------|
| GREEN    | < 500          | Near-perfect instruction following.            |
| YELLOW   | 500 -- 2,000   | Slight degradation. Compression recommended.  |
| ORANGE   | 2,000 -- 5,000 | Significant degradation. Restructure needed.  |
| RED      | 5,000 -- 10,000| Instructions actively degrading.              |
| CRITICAL | > 10,000       | Instructions indistinguishable from noise.    |

## Requirements

- Claude Code CLI
- Python 3.10+ (stdlib only -- zero external dependencies)
- For exact token counting: `ANTHROPIC_API_KEY` in your environment, plus `curl` and `jq`
- Without API key: Python fallback counts tokens at ~94% accuracy

## Installation

Clone into your project's skills directory:

```bash
# From your project root
mkdir -p .claude/skills
git clone https://github.com/YOUR_USERNAME/context-analyser.git .claude/skills/context-analyser
```

Or as a git submodule:

```bash
git submodule add https://github.com/YOUR_USERNAME/context-analyser.git .claude/skills/context-analyser
```

Claude Code detects the skill automatically from `.claude/skills/`.

## Usage

### Commands

| Command          | What It Does                                      |
|------------------|---------------------------------------------------|
| `/audit`         | Analyse token usage. Read-only, always safe.      |
| `/compress`      | Rewrite instructions concisely (phase 1).         |
| `/restructure`   | Apply layered architecture (phase 2).             |
| `/tier`          | Split into tiered files (phase 3).                |
| `/context-check` | Full pipeline: audit, then escalate as needed.    |

### Example

```
> /audit

========================================================================
  CLAUDE.MD TOKEN AUDIT
========================================================================

  File:      /home/user/project/CLAUDE.md
  Method:    anthropic_api (exact)
  Total:     2,340 tokens
  Zone:      [##] ORANGE
  Action:    Restructure required. Apply layered architecture.

------------------------------------------------------------------------
  SECTION BREAKDOWN (largest first)
------------------------------------------------------------------------
    890 tok   38.0%  [##] ORANGE   ##########  Database Conventions
    520 tok   22.2%  [!!] YELLOW   ######      Export Format Spec
    380 tok   16.2%  [OK] GREEN    #####       UI Component Patterns
    210 tok    9.0%  [OK] GREEN    ###         Universal Rules
    180 tok    7.7%  [OK] GREEN    ##          Project Identity
    160 tok    6.8%  [OK] GREEN    ##          Context Management

------------------------------------------------------------------------
  PROJECTED OUTCOME
------------------------------------------------------------------------
    Current:   2,340 tokens ([##] ORANGE)
    Projected:   630 tokens ([!!] YELLOW)
    Reduction: 73.1%
========================================================================
```

### Optional: Auto-Audit on Session Start

Add this line to your CLAUDE.md:

```
Run /audit at the start of each session.
```

### Direct Script Usage

Run the token counter without the skill:

```bash
# Exact count (requires API key)
./scripts/count_tokens.sh CLAUDE.md

# Offline count (~94% accuracy)
python scripts/count_tokens.py CLAUDE.md

# JSON output
python scripts/count_tokens.py CLAUDE.md --json
```

## Security

This skill runs inside Claude Code which has access to your API key, file system, and project source. Security is structural, not aspirational:

- **Zero external dependencies.** All Python is pure stdlib. No pip. Nothing to compromise via supply chain.
- **Python never touches the network.** Only `count_tokens.sh` (bash + curl) makes API calls.
- **No eval, exec, pickle, subprocess.** All code paths are statically determinable.
- **Input paths validated and sandboxed.** Symlink escapes caught. Path traversal blocked.
- **AST security scanner included.** Run `python scripts/self_test.py` to verify compliance.

## Project Structure

```
context-analyser/
+-- SKILL.md                         Core skill (488 tokens, GREEN zone)
+-- scripts/
|   +-- count_tokens.sh              Bash exact counter (Anthropic API)
|   +-- count_tokens.py              Python fallback (stdlib only)
|   +-- boundary_check.py            Scope enforcement (stdlib only)
|   +-- self_test.py                 Security AST scanner (stdlib only)
+-- references/
|   +-- compression.md               Phase 1 guidance
|   +-- restructuring.md             Phase 2 guidance
|   +-- layered-architecture.md      5-layer model reference
|   +-- tiering.md                   Phase 3 guidance
|   +-- context-rot-thresholds.md    Zone data (Chroma research)
|   +-- boundary-score.md            Scope governance spec
+-- tests/
    +-- test_count_tokens.py         57 tests
    +-- test_boundary_check.py       32 tests
    +-- KNOWN_TEST_GAPS.md           V2 test backlog
```

## How It Works

Built on [Chroma's context rot research](https://research.trychroma.com/context-rot) (July 2025), which tested 18 frontier models. Key findings:

- Claude Sonnet 4 holds near-perfect recall up to ~300 tokens, degrades to ~0.94 at 1K, hits floor (~0.50) by 8K
- All models converge to coin-flip accuracy by 10K tokens
- Logically structured context performs WORSE than shuffled (structured text creates plausible distractors)
- Even a single distractor reduces performance, and the effect compounds

The skill defines token budget zones and a tiered architecture that keeps your CLAUDE.md core lean while making domain-specific instructions available on demand.

## Contributing

1. All Python must use stdlib only. Run `python scripts/self_test.py` before submitting.
2. All tests must pass: `python -m pytest tests/ -v`
3. SKILL.md must stay under 500 tokens.
4. No external dependencies. Ever. See the security policy in the spec docs.

## Roadmap

See [CHANGELOG.md](CHANGELOG.md) for version history and [tests/KNOWN_TEST_GAPS.md](tests/KNOWN_TEST_GAPS.md) for the V2 test backlog.

Planned V2 enhancements:
- Session-start hook for automatic detection
- Keyword-based domain classification in tier recommendations
- npm plugin distribution

## Licence

[MIT](LICENSE)

## Acknowledgements

- [Chroma Research](https://research.trychroma.com/context-rot) for the context rot benchmarks
- [Anthropic](https://anthropic.com) for Claude Code and the token counting API

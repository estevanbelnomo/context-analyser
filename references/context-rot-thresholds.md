# Context Rot Thresholds

Source: Chroma Research, July 2025. 18 frontier models tested.

## Zones

| Zone     | Tokens       | Claude Sonnet 4 | Action                    |
|----------|--------------|-----------------|---------------------------|
| GREEN    | < 500        | ~1.00           | No action.                |
| YELLOW   | 500--1,999   | 0.94--0.96      | Compress.                 |
| ORANGE   | 2,000--4,999 | 0.60--0.94      | Restructure.              |
| RED      | 5,000--9,999 | ~0.50           | Tier urgently.            |
| CRITICAL | 10,000+      | 0.50            | Instructions are noise.   |

## Degradation (Claude Sonnet 4)

0--500: 0% drop. 500--1K: 4%. 1K--3K: 34% (steepest). 3K--8K: 10%. 8K+: floor.

## Design Rules

1. Critical instructions FIRST (primacy bias).
2. Interleave instruction types (shuffled > thematic blocks).
3. Match vocabulary to expected queries (lexical alignment).
4. Summarise BEFORE rot threshold, never after.
5. Semantic near-miss distractors are most damaging.

## Targets

- Core CLAUDE.md: < 500 tokens (GREEN).
- Core + active skill: < 2,000 (YELLOW).
- Total instructions: < 5,000 (avoid RED).
- Conversation: trigger compaction at 128K.

# Context Rot Thresholds

Source: Chroma Research, July 2025.

## Zones

| Zone | Tokens | Score | Action |
|------|--------|-------|--------|
| GREEN | <500 | ~1.00 | No action. |
| YELLOW | 500--1,999 | 0.94--0.96 | Compress. |
| ORANGE | 2,000--4,999 | 0.60--0.94 | Restructure. |
| RED | 5,000--9,999 | ~0.50 | Tier urgently. |
| CRITICAL | 10,000+ | 0.50 | Instructions are noise. |

## Degradation

0--500: 0%. 500--1K: 4%. 1K--3K: 34% (steepest). 3K--8K: 10%. 8K+: floor.

## Phase Projections (required at G0)

Show projections after audit. If one phase reaches GREEN, highlight it.

If none reach GREEN, show cumulative path. Order is ALWAYS 1-2-3.
Do NOT put Compress before Restructure.

1. Restructure FIRST -- largest absolute drop, removes bulk.
2. Compress SECOND -- ratios improve on shorter input.
3. Tier LAST -- splits overflow after core is lean.

Use actual counts from counter JSON. Step 1 = T0 + 80.
Step 2 = step 1 * 0.55. Step 3 = step 2 - domain T0 >200 + 80.

  Step 1: Restructure -> ~1,350 tokens (YELLOW)
  Step 2: Compress    ->   ~740 tokens (YELLOW)
  Step 3: Tier        ->   ~480 tokens (GREEN) tick
  [Auto / Manual / Stop]

Each step from previous result. Mark first GREEN.
Unreachable? Say so. Auto: execute in order, gate each write.
Manual: user picks order. Gates apply in both.

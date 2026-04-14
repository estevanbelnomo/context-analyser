# Phase 1: Compression

Rewrite concisely, preserve meaning. Target: 30-50% reduction.

## Rules

1. **Remove filler**: "You should always make sure to" -> start with verb.
   "It is important that" / "Please note that" -> delete.
2. **Merge redundant**: Two rules saying the same thing -> one.
   "Use parameterised queries" + "Never string interpolate SQL"
   -> "Parameterised SQL only. No string interpolation."
3. **Remove self-evident context**: If stack stated in identity, don't repeat.
4. **Compress examples**: 5-line code block -> one-line pattern description.
5. **Inline lists**: Vertical bullet lists -> comma-separated inline.
6. **Remove meta-instructions**: "Think step by step", "Be careful" (implicit).

## Semantic Check (boundary_check.py)

Before proposing any rewrite:
1. Keyword Jaccard >= 0.55 between original and rewrite.
2. ALL original negations preserved. No new negations added.
3. Imperative polarity unchanged (positive/negative/neutral).

If any check fails: keep original, flag for user review.
Conservative: false positives acceptable, false negatives not.

## Workflow

1. Parse into sections. Compress each.
2. Run semantic check per rewrite.
3. Show before/after diff + token counts.
4. GATE 1: [Apply all] [Apply selected] [Skip] [Stop].
5. GREEN (< 500)? Done. Otherwise recommend Phase 2.

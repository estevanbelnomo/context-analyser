# Phase 3: Tiering

Last resort. Only when post-compression + post-restructure core > 500.

## Taxonomy

| Tier | Loading          | Budget    | Content                        |
|------|------------------|-----------|--------------------------------|
| 0    | Always loaded    | < 500     | Identity, rules, index         |
| 1    | Auto on trigger  | < 800 ea  | Domain rules, patterns         |
| 2    | Slash cmd / cond | < 1,500 ea| Checklists, specs, examples    |
| 3    | User request     | Unlimited | Historical, legacy, rare       |

Max concurrent: T0+T1+T2 = 500+800+1,500 = 2,800 (YELLOW).

## Decision Logic

Every task? -> T0. Domain-specific? -> T1. Checklist/spec? -> T2.
Monthly or less? -> T3. "Mistake on typical task if removed?" YES->T0/T1.

## Trigger Keywords (Tier 1)

3-6 per file. Nouns not verbs. Include synonyms. MUST be disjoint.

## Validation

1. Trigger keywords disjoint across T1 files.
2. T1 files must not cross-reference each other.
3. Every T2 referenced by T1 or slash cmd. Max concurrent <2,800.

Do not tier files <800 tok or single-domain projects.

## Workflow

1. Apply tier logic to remaining sections.
2. Define disjoint trigger keywords.
3. Validate. Verify max concurrent <2,800.
4. GATE 3: [Apply] [Modify] [Stop].
5. Execute moves. Update routing index. Final count.

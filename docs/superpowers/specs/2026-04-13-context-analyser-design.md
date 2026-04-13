# Context Analyser Skill: Final Specification

## Status: Approved for Build

This document is the single definitive reference for building the context-analyser
skill. It supersedes all prior drafts and working documents. Every design decision,
security constraint, and implementation detail is captured here.

---

## 1. What This Skill Does

Analyses and optimises CLAUDE.md files for token efficiency and context rot
mitigation. Runs a four-phase escalating pipeline: Audit, Compress, Restructure,
Tier. Each phase only runs if the previous did not bring the file into the GREEN
zone (< 500 tokens).

The skill follows the same tiered architecture it teaches (Approach 2: Skill Family).
The core SKILL.md stays under 500 tokens. Phase-specific guidance loads JIT from
reference files.

---

## 2. Architecture: Skill Family

### File Tree

```
context-analyser/
|
+-- SKILL.md                           Core: audit + routing (< 500 tokens)
|
+-- scripts/
|   +-- count_tokens.sh                Bash exact counter (Anthropic API)
|   +-- count_tokens.py                Python fallback (stdlib only, ~94%)
|   +-- boundary_check.py              Python boundary enforcement (stdlib only)
|   +-- self_test.py                   Python self-test suite (stdlib only)
|
+-- references/
    +-- compression.md                 Phase 1 guidance (< 800 tokens)
    +-- restructuring.md               Phase 2 guidance (< 800 tokens)
    +-- layered-architecture.md        5-layer model ref (< 1,200 tokens)
    +-- tiering.md                     Phase 3 guidance (< 800 tokens)
    +-- context-rot-thresholds.md      Zone data from Chroma (< 600 tokens)
    +-- boundary-score.md              Scope governance spec (< 1,000 tokens)
```

### Token Budgets

| File                        | Budget    | Loading                              |
|-----------------------------|-----------|--------------------------------------|
| SKILL.md                    | < 500 tok | Always loaded                        |
| compression.md              | < 800 tok | Phase 1 only                         |
| restructuring.md            | < 800 tok | Phase 2 only                         |
| layered-architecture.md     | < 1,200 tok | Phase 2 reference                  |
| tiering.md                  | < 800 tok | Phase 3 only                         |
| context-rot-thresholds.md   | < 600 tok | Audit phase                          |
| boundary-score.md           | < 1,000 tok | Skill initialisation               |
| scripts/*.sh, scripts/*.py  | N/A       | Executed, never loaded into context  |

**Maximum concurrent context:** SKILL.md + largest reference = 500 + 1,200 = 1,700 tokens.
This stays in the YELLOW zone even during the heaviest phase (phase 2).

---

## 3. Python Security Policy

This section is a HARD CONSTRAINT on every Python file in the skill.
It applies to count_tokens.py, boundary_check.py, self_test.py, and
any future Python file added to the skill.

### 3.1 Threat Model

The skill runs inside Claude Code, which has access to:
- The user's Anthropic API key (in environment)
- The user's file system (project source, credentials, config)
- Network access (to allowed domains)

A compromised Python dependency could exfiltrate any of these. Recent supply
chain attacks (ultralytics, pytoiltoil, colours.js, event-stream) demonstrate
this is not theoretical. The blast radius of a compromised skill dependency
is the user's entire development environment.

### 3.2 Absolute Rules

Every Python file in this skill MUST comply with ALL of the following.
Violation of any single rule is grounds to reject the file.

```
RULE 1: ZERO EXTERNAL DEPENDENCIES
  - No pip install. No requirements.txt. No pyproject.toml dependencies.
  - Every import must resolve to a Python stdlib module.
  - Permitted imports (exhaustive list):
      from __future__ import annotations
      import ast
      import json
      import re
      import sys
      from collections import Counter
      from pathlib import Path
  - Any import not on this list requires explicit justification and
    approval before being added.

RULE 2: NO DANGEROUS BUILTINS
  - No eval(), exec(), compile(), __import__(), importlib, pickle, marshal, ctypes, cffi

RULE 3: NO NETWORK ACCESS
  - No socket, urllib, http, xmlrpc, ftplib, smtplib, poplib, imaplib, ssl, webbrowser
  - The ONLY code that touches the network is count_tokens.sh (bash + curl).

RULE 4: NO SUBPROCESS / OS COMMAND EXECUTION
  - No subprocess, os.system(), os.popen(), os.exec*(), os.spawn*(), pty, commands

RULE 5: NO DYNAMIC CODE LOADING
  - No importlib, __import__(), runpy, zipimport, pkgutil, imp

RULE 6: INPUT VALIDATION
  - Every file path: reject null bytes, resolve to absolute, verify within allowed roots,
    verify regular file, verify .md extension for instruction files.

RULE 7: COMPILE-TIME REGEX ONLY
  - All regex patterns defined as module-level constants via re.compile().
  - No regex patterns constructed from user input.

RULE 8: AUDITABLE IN FULL
  - < 300 lines per file (hard limit: 500). No minified/obfuscated code.
  - No base64-encoded strings. No hex-encoded strings > 16 characters.
```

### 3.3 Enforcement

The skill includes self_test.py that statically analyses all Python files via AST
and verifies compliance with Rules 1-5 and 8.

### 3.4 Future Dependencies

Not permitted. See Section 3.2. If a future contributor believes an external library
is necessary, they must document why stdlib is insufficient, audit the library source,
pin exact version with hash, add to AST scanner, and re-run full security scan.

---

## 4. Trigger Model

| Trigger           | Mechanism                                                          |
|-------------------|--------------------------------------------------------------------|
| Session start     | Optional. User adds `Run /audit at session start` to their CLAUDE.md. |
| On-demand         | `/audit`, `/compress`, `/restructure`, `/tier`, `/context-check`   |
| Description match | context rot, instruction bloat, token budget, "forgetting/ignoring instructions", CLAUDE.md optimisation |

---

## 5. Pipeline

### Phase 0: Audit (read-only, always safe)

Loads: references/context-rot-thresholds.md, references/boundary-score.md
Executes: scripts/count_tokens.sh (or .py fallback)
Checks: SCOPE_CONTAINMENT on every file read

Steps:
1. Validate target file is in scope.
2. Run token counter on full file.
3. Parse into sections by markdown headers.
4. Count tokens per section.
5. Sort by token count descending.
6. Recommend tier for each section.
7. Calculate projected core if tiered.
8. Check boundary warnings (near zone thresholds).
9. Generate and present report.
10. GATE 0: [Auto-restructure] [Manual edit] [Stop]

If Manual edit chosen: prompt (i) Stop analysis, or (ii) Analyse later
(next session start or configurable delay).

### Phase 1: Compress (same meaning, fewer tokens)

Loads: references/compression.md
Checks: SEMANTIC_BOUNDARY on every rewrite, CONFIRMATION_GATES (Gate 1)

Steps:
1. For each section, generate compressed rewrite.
2. Run semantic preservation check (keyword Jaccard >= 0.55, negations preserved,
   imperative polarity unchanged).
3. If check fails, keep original text.
4. Count tokens on each rewrite.
5. Generate before/after diffs.
6. GATE 1: [Apply all] [Apply selected] [Skip] [Stop]
7. If GREEN, stop. Otherwise recommend Phase 2.

Target: 30-50% token reduction.

### Phase 2: Restructure (apply 5-layer architecture)

Loads: references/restructuring.md, references/layered-architecture.md
Checks: FILE_TREE_CONTAINMENT, SCOPE_CONTAINMENT, CONFIRMATION_GATES (Gate 2)

Steps:
1. Classify sections into Layer 1 (core), 2 (skill), 3 (reference).
2. Generate new CLAUDE.md core (Layer 1 + routing index).
3. Generate .claude/*.md skill file stubs (Layer 2).
4. Generate docs/*.md reference file stubs (Layer 3).
5. Verify core < 500 tokens, skill files < 800 tokens.
6. GATE 2: [Apply] [Modify] [Stop]
7. Write files. If GREEN, stop. Otherwise recommend Phase 3.

### Phase 3: Tier (decompose into Tier 0/1/2/3)

Loads: references/tiering.md
Checks: FILE_TREE_CONTAINMENT, CONFIRMATION_GATES (Gate 3), STATELESS

Steps:
1. Apply tier decision logic to remaining core content.
2. Define trigger keywords per Tier 1 file (3-6, disjoint).
3. Validate: no collisions, no circular refs, no orphans.
4. Max concurrent context (T0 + largest T1 + largest T2) < 2,800 tokens.
5. GATE 3: [Apply] [Modify] [Stop]
6. Execute file moves. Update routing index.
7. Final count. Report. STATELESS check.

---

## 6. Token Counting

### Primary: Bash (exact)

Script: scripts/count_tokens.sh
Requires: ANTHROPIC_API_KEY, curl, jq
Accuracy: 100% (Anthropic API)
Used in: Phase 0 (audit), Phase 3 (final validation)

### Fallback: Python (offline, ~94%)

Script: scripts/count_tokens.py
Requires: Python 3.10+ (stdlib only)
Accuracy: ~94% (+/- 6%) via calibrated regex pre-tokenizer
Used in: Phase 1 (compression deltas), Phase 2 (core validation)

### Zone Thresholds

| Zone     | Token Range    | Claude Sonnet 4 Levenshtein | Action                          |
|----------|----------------|-----------------------------|---------------------------------|
| GREEN    | < 500          | ~1.00                       | No action needed.               |
| YELLOW   | 500 -- 2,000   | 0.94 -- 0.96                | Compression recommended.        |
| ORANGE   | 2,000 -- 5,000 | 0.60 -- 0.94                | Restructure required.           |
| RED      | 5,000 -- 10,000| ~0.50                       | Urgent. Tiering required.       |
| CRITICAL | > 10,000       | 0.50                        | Immediate decomposition needed. |

Source: Chroma Research, July 2025.

---

## 7. Scope Governance (Boundary Score)

| ID | Boundary             | Guards                                     | Max | Hard Block If                    |
|----|----------------------|--------------------------------------------|-----|----------------------------------|
| A  | Scope Containment    | Only instruction files                     | 30  | Target file out of scope         |
| B  | Confirmation Gates   | Never auto-apply without diff              | 20  | Write without gate confirmation  |
| C  | Semantic Boundary    | Editor, not author                         | 20  | Meaning altered                  |
| E  | File Tree Containment| Writes to .claude/, CLAUDE.md, docs/ only  | 15  | Write outside instruction tree   |
| F  | Statelessness        | No cross-session state                     | 10  | Cache/state file created         |
| G  | Network Isolation    | Python never touches network               | 5   | Banned import in AST scan        |

Score 80-100: Proceed. 50-79: Ask user. 0-49: Blocked. Any boundary at 0: Blocked.

---

## 8. Build Order

| Step | Component                              | Test Criteria                                      |
|------|----------------------------------------|----------------------------------------------------|
| 1    | scripts/count_tokens.sh                | Exact count matching API. Handles missing key.     |
| 2    | scripts/count_tokens.py                | Within 6% of bash count. Zero external imports.    |
| 3    | scripts/self_test.py                   | Scans .py files. Reports violations. Exits 0/1.   |
| 4    | scripts/boundary_check.py              | Catches negation drops + polarity flips.           |
| 5    | references/context-rot-thresholds.md   | Reference doc.                                     |
| 6    | references/boundary-score.md           | Matches boundary_check.py logic.                   |
| 7    | SKILL.md                               | < 500 tokens. /audit triggers correctly.           |
| 8    | Phase 0: Audit pipeline                | Report matches expected counts.                    |
| 9    | references/compression.md              | Reference doc for phase 1.                         |
| 10   | Phase 1: Compress pipeline             | 30-50% reduction. Semantic checks pass.            |
| 11   | references/restructuring.md + layered-architecture.md | Reference docs for phase 2.       |
| 12   | Phase 2: Restructure pipeline          | Core < 500. Skill files < 800.                     |
| 13   | references/tiering.md                  | Reference doc for phase 3.                         |
| 14   | Phase 3: Tier pipeline                 | No collisions/orphans. Max concurrent < 2,800.     |
| 15   | Integration test                       | Full /context-check on real CLAUDE.md.             |
| 16   | Security verification                  | self_test.py passes. Manual grep confirms.         |

---

## 9. Success Criteria

1. `/audit` produces accurate, actionable reports on any CLAUDE.md.
2. Full pipeline brings ORANGE (2K-5K) to GREEN core (< 500) with no intent loss.
3. All six boundary checks pass on every action.
4. SKILL.md itself < 500 tokens.
5. Max concurrent context < 1,700 tokens.
6. ALL Python: zero external deps, passes AST scan.
7. Bash counter: exact counts matching Anthropic API.
8. `self_test.py` exits 0 on all skill Python files.

---

## 10. Explicitly Out of Scope (V1)

| Enhancement                    | Why Deferred                                         |
|--------------------------------|------------------------------------------------------|
| Session-start hook             | Approach 3 add-on. Build after core proves value.    |
| Diff tracking between audits   | Requires opting out of STATELESS rule.               |
| Multi-file directory scanning  | Scope creep. V1 handles one CLAUDE.md at a time.     |
| Custom zone thresholds         | Default thresholds work for all current models.      |
| Per-edit granular accept/reject| Phase-level gates are sufficient for V1.             |
| External library dependencies  | Never. See Section 3.                                |

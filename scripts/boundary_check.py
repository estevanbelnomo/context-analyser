#!/usr/bin/env python3
"""
Boundary enforcement for context-analyser skill.
ZERO external dependencies. Stdlib only. Auditable in full.

Implements the six-boundary scoring system:
  A: Scope Containment (30 pts)
  B: Confirmation Gates (20 pts)
  C: Semantic Boundary (20 pts)
  E: File Tree Containment (15 pts)
  F: Statelessness (10 pts)
  G: Network Isolation (5 pts)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


# == Filler Words (for semantic check) ===========================

_FILLER_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "that",
    "this", "it", "its", "and", "or", "but", "if", "then", "than",
    "so", "very", "just", "also", "all", "any", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "only",
    "own", "same", "too", "about", "up", "out", "when", "where",
    "which", "while", "who", "whom", "how", "what", "there",
    "please", "note", "important", "make", "sure", "always",
    "you", "your", "we", "our",
})

# == Negation Detection ==========================================

_NEGATION_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:never|no|not|don't|dont|do\s+not|cannot|can't|cant"
    r"|shouldn't|shouldnt|should\s+not|mustn't|mustnt|must\s+not"
    r"|won't|wont|will\s+not|wouldn't|wouldnt|would\s+not"
    r"|avoid|prohibit|forbid|disallow|reject|exclude"
    r"|without|neither|nor)\b",
    re.IGNORECASE,
)

_NEGATION_CONTEXT_PATTERN: re.Pattern[str] = re.compile(
    r"(?:never|no|not|don't|dont|do\s+not|cannot|can't|cant"
    r"|shouldn't|shouldnt|should\s+not|mustn't|mustnt|must\s+not"
    r"|won't|wont|will\s+not|wouldn't|wouldnt|would\s+not"
    r"|avoid|prohibit|forbid|disallow|reject|exclude"
    r"|without|neither|nor)"
    r"\s+(\w+(?:\s+\w+){0,3})",
    re.IGNORECASE,
)

# == Keyword Extraction ==========================================

_WORD_PATTERN: re.Pattern[str] = re.compile(r"[a-zA-Z_]\w*")


def extract_keywords(text: str) -> Counter:
    """
    Extract meaningful keywords from text, filtering filler words.
    Returns Counter of keyword frequencies.
    """
    words = _WORD_PATTERN.findall(text.lower())
    return Counter(w for w in words if w not in _FILLER_WORDS and len(w) > 1)


def extract_negations(text: str) -> list[str]:
    """
    Extract negation contexts from text.
    Returns list of "negation + target" strings.
    """
    return [m.group(0).lower().strip() for m in _NEGATION_CONTEXT_PATTERN.finditer(text)]


# == Imperative Polarity =========================================

_POSITIVE_IMPERATIVES: re.Pattern[str] = re.compile(
    r"\b(?:use|always|must|require|ensure|prefer|include|add|enable)\b",
    re.IGNORECASE,
)

_NEGATIVE_IMPERATIVES: re.Pattern[str] = re.compile(
    r"\b(?:never|avoid|prohibit|forbid|disallow|reject|exclude"
    r"|remove|disable|don't|do\s+not|no)\b",
    re.IGNORECASE,
)


def classify_polarity(text: str) -> str:
    """Classify imperative polarity as positive, negative, or neutral."""
    pos = len(_POSITIVE_IMPERATIVES.findall(text))
    neg = len(_NEGATIVE_IMPERATIVES.findall(text))
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


# == Semantic Boundary Check =====================================


def check_semantic_preservation(original: str, proposed: str) -> dict:
    """
    Check if a proposed rewrite preserves the semantic intent of the original.

    Returns dict with:
      - passed: bool
      - keyword_jaccard: float
      - negations_preserved: bool
      - polarity_preserved: bool
      - issues: list[str]
    """
    issues: list[str] = []

    # 1. Keyword Jaccard similarity
    orig_kw = set(extract_keywords(original))
    prop_kw = set(extract_keywords(proposed))

    if orig_kw or prop_kw:
        intersection = orig_kw & prop_kw
        union = orig_kw | prop_kw
        jaccard = len(intersection) / len(union) if union else 1.0
    else:
        jaccard = 1.0

    if jaccard < 0.55:
        issues.append(
            f"Keyword overlap too low: {jaccard:.2f} (threshold: 0.55). "
            f"Lost keywords: {orig_kw - prop_kw}"
        )

    # 2. Negation preservation
    orig_negs = extract_negations(original)
    prop_negs = extract_negations(proposed)

    orig_neg_targets = {n.split()[-1] for n in orig_negs if n.split()}
    prop_neg_targets = {n.split()[-1] for n in prop_negs if n.split()}

    missing_negations = orig_neg_targets - prop_neg_targets
    added_negations = prop_neg_targets - orig_neg_targets

    negations_ok = True
    if missing_negations:
        issues.append(f"Negations dropped: {missing_negations}")
        negations_ok = False
    if added_negations:
        issues.append(f"New negations added: {added_negations}")
        negations_ok = False

    # 3. Imperative polarity
    orig_pol = classify_polarity(original)
    prop_pol = classify_polarity(proposed)

    polarity_ok = True
    if orig_pol != prop_pol and orig_pol != "neutral" and prop_pol != "neutral":
        issues.append(
            f"Polarity flipped: {orig_pol} -> {prop_pol}"
        )
        polarity_ok = False

    passed = jaccard >= 0.55 and negations_ok and polarity_ok

    return {
        "passed": passed,
        "keyword_jaccard": round(jaccard, 3),
        "negations_preserved": negations_ok,
        "polarity_preserved": polarity_ok,
        "issues": issues,
    }


# == Scope Containment (Boundary A) ==============================


def is_instruction_file(path: Path) -> str:
    """
    Classify whether a path is an instruction file.
    Returns: "yes", "ambiguous", or "no".
    """
    resolved = path.resolve()
    name = resolved.name

    if name == "CLAUDE.md":
        return "yes"

    parts_str = str(resolved)
    if ".claude" in parts_str:
        return "yes"

    if name.endswith(".md") and "docs" in parts_str:
        return "ambiguous"

    return "no"


# == File Tree Containment (Boundary E) ==========================


def is_in_instruction_tree(path: Path) -> bool:
    """Check if a write target is within the allowed instruction tree."""
    resolved = path.resolve()
    name = resolved.name
    parts_str = str(resolved)

    if name == "CLAUDE.md":
        return True
    if ".claude" in parts_str:
        return True
    if name.endswith(".md") and "docs" in parts_str:
        return True
    return False


# == Full Pre-Flight Check =======================================


def preflight_check(
    target_files: list[str],
    write_targets: list[str],
    action_type: str,
    is_read_only: bool = False,
    has_confirmation_gate: bool = True,
    references_prior_session: bool = False,
    involves_python_network: bool = False,
) -> dict:
    """
    Run the full boundary score pre-flight check.

    Returns dict with score, classification, and issues.
    """
    issues: list[str] = []
    score = 0.0

    # Boundary A: Scope Containment (30 pts)
    if target_files:
        per_file = 30.0 / len(target_files)
        for tf in target_files:
            status = is_instruction_file(Path(tf))
            if status == "yes":
                score += per_file
            elif status == "ambiguous":
                score += per_file * (10.0 / 30.0)
                issues.append(
                    f"[A] Ambiguous target: {tf}. "
                    "Confirm it is an instruction file."
                )
            else:
                issues.append(
                    f"[A] HARD BLOCK: {tf} is outside instruction file scope."
                )
                return {"score": 0, "classification": "VIOLATION", "issues": issues}
    else:
        score += 30

    # Boundary B: Confirmation Gates (20 pts)
    if is_read_only:
        score += 20
    elif has_confirmation_gate:
        score += 15
    else:
        issues.append("[B] HARD BLOCK: Write action without confirmation gate.")
        return {"score": 0, "classification": "VIOLATION", "issues": issues}

    # Boundary C: Semantic Scope (20 pts)
    structural_types = {"reorder", "classify", "count", "audit"}
    confirmed_types = {"compress", "deduplicate"}
    blocked_types = {"add_instruction", "remove_instruction", "alter_meaning"}

    if action_type in structural_types:
        score += 20
    elif action_type in confirmed_types:
        score += 15
    elif action_type in blocked_types:
        issues.append(
            f"[C] HARD BLOCK: '{action_type}' violates semantic boundary."
        )
        return {"score": 0, "classification": "VIOLATION", "issues": issues}
    else:
        score += 10
        issues.append(f"[C] Unknown action type: '{action_type}'. Review manually.")

    # Boundary E: File Tree Containment (15 pts)
    if write_targets:
        per_target = 15.0 / len(write_targets)
        for wt in write_targets:
            if is_in_instruction_tree(Path(wt)):
                score += per_target
            else:
                issues.append(
                    f"[E] HARD BLOCK: Write target {wt} outside instruction tree."
                )
                return {"score": 0, "classification": "VIOLATION", "issues": issues}
    else:
        score += 15

    # Boundary F: Statelessness (10 pts)
    if not references_prior_session:
        score += 10
    else:
        issues.append("[F] HARD BLOCK: Action references prior session state.")
        return {"score": 0, "classification": "VIOLATION", "issues": issues}

    # Boundary G: Network Isolation (5 pts)
    if not involves_python_network:
        score += 5
    else:
        issues.append("[G] HARD BLOCK: Python network call detected.")
        return {"score": 0, "classification": "VIOLATION", "issues": issues}

    # Classify
    final_score = round(score)
    if final_score >= 80:
        classification = "CLEAR"
    elif final_score >= 50:
        classification = "AMBIGUOUS"
    else:
        classification = "VIOLATION"

    return {
        "score": final_score,
        "classification": classification,
        "issues": issues,
    }


# == Report Formatter ============================================


def format_preflight_report(result: dict) -> str:
    """Format pre-flight check result as human-readable report."""
    out: list[str] = []

    out.append(
        f"BOUNDARY CHECK: {result['classification']} "
        f"(score: {result['score']}/100)"
    )
    out.append("")

    if result["issues"]:
        out.append("  Issues:")
        for issue in result["issues"]:
            out.append(f"  {issue}")
    else:
        out.append("  All boundaries passed.")

    return "\n".join(out)


# == Entry Point =================================================


def main() -> None:
    """CLI entry point for boundary checking."""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.stdout.write(
            "Usage: python boundary_check.py --check <json-action>\n"
            "       python boundary_check.py --semantic <original> <proposed>\n"
            "\n"
            "  --check    Run pre-flight check on a JSON action descriptor\n"
            "  --semantic Compare original and proposed text for semantic preservation\n"
        )
        sys.exit(0)

    if sys.argv[1] == "--semantic" and len(sys.argv) >= 4:
        original = sys.argv[2]
        proposed = sys.argv[3]
        result = check_semantic_preservation(original, proposed)
        sys.stdout.write(json.dumps(result, indent=2))
        sys.stdout.write("\n")
        sys.exit(0 if result["passed"] else 1)

    if sys.argv[1] == "--check" and len(sys.argv) >= 3:
        action = json.loads(sys.argv[2])
        result = preflight_check(**action)
        sys.stdout.write(json.dumps(result, indent=2))
        sys.stdout.write("\n")
        report = format_preflight_report(result)
        sys.stderr.write(report)
        sys.stderr.write("\n")
        sys.exit(0 if result["classification"] != "VIOLATION" else 1)

    sys.stderr.write("Unknown command. Use --help for usage.\n")
    sys.exit(1)


if __name__ == "__main__":
    main()

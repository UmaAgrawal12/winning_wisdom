"""
Hook Validator - Detects weak hooks and suggests improvements
============================================================
Quick validation to catch abstract/weak hooks before full scoring.
"""

import re
from typing import Tuple


def is_abstract_hook(hook_lines: str) -> Tuple[bool, str]:
    """
    Quick check if hook is too abstract/philosophical.

    Args:
        hook_lines: First 2-3 lines of the script

    Returns:
        (is_abstract: bool, reason: str)
    """
    hook_lower = hook_lines.lower()

    # Abstract/philosophical patterns
    abstract_patterns = [
        r"it's (strange|odd|interesting) how",
        r"there's (something|a kind|a way)",
        r"you (ever|always|never) (find|feel|think)",
        r"have you ever",
        r"sometimes (you|we|it)",
        r"the (thing|way|cost|price)",
        r"what (blocks|stands|matters)",
        r"it (feels|seems|looks) like",
        r"life (doesn't|does|is)",
        r"time (slips|passes|waits)",
        r"obstacles (feel|seem|are)",
        r"fear (is|was|becomes)",
        r"anger (is|was|becomes)",
        r"waiting (is|was|becomes)",
        r"i used to (think|believe|feel)",
        r"most (days|mornings|evenings)",
        r"you (know|see|find) (how|that|when)",
        r"there (comes|was) a (time|moment|point)",
        r"(anger|fear|pride|doubt) (can|will|does)",
    ]

    # Check for abstract patterns
    for pattern in abstract_patterns:
        if re.search(pattern, hook_lower):
            return True, f"Contains abstract pattern: '{pattern}'"

    # Check for concrete indicators (good signs)
    concrete_indicators = [
        r"i (saw|watched|knew|met|taught)",
        r"most people i (knew|saw|watched|met)",
        r"\d+ (students|people|years)",
        r"forty years",
        r"in my class",
        r"three students",
        r"good people",
    ]

    has_concrete = any(re.search(indicator, hook_lower) for indicator in concrete_indicators)

    # If no concrete indicators and has abstract feel, mark as abstract
    if not has_concrete and len(hook_lines.split('\n')) >= 2:
        # Check if it's a generic question
        if hook_lines.strip().endswith('?'):
            return True, "Generic question format"

        # Check if it starts with vague statements
        first_line = hook_lines.split('\n')[0].lower()
        vague_starters = [
            "you ever", "have you", "sometimes", "there's",
            "it's", "life", "time", "the thing", "what",
            "anger", "fear", "pride", "doubt", "most days",
        ]
        if any(first_line.startswith(starter) for starter in vague_starters):
            return True, "Starts with vague/abstract language"

    return False, ""


def validate_hook_strength(hook_lines: str) -> Tuple[bool, str]:
    """
    Validate if hook is strong enough (concrete and specific).

    Args:
        hook_lines: First 2-3 lines of the script

    Returns:
        (is_strong: bool, feedback: str)
    """
    is_abstract, reason = is_abstract_hook(hook_lines)

    if is_abstract:
        return False, f"Weak hook detected: {reason}. Hook should be concrete and specific, not abstract."

    # Check for specific concrete elements
    hook_lower = hook_lines.lower()

    concrete_score = 0

    # Specific observations — high value
    if re.search(r"i (saw|watched|knew|met)", hook_lower):
        concrete_score += 2
    if re.search(r"most people i", hook_lower):
        concrete_score += 2
    if re.search(r"\d+ (students|people|years)", hook_lower):
        concrete_score += 2
    if re.search(r"(in my class|forty years|three students)", hook_lower):
        concrete_score += 2

    # Personal experience — lower value
    if re.search(r"(i learned|i remember|i saw)", hook_lower):
        concrete_score += 1

    # Stricter threshold — must score 3+ to pass
    if concrete_score >= 3:
        return True, "Hook is concrete and specific"
    elif concrete_score >= 1:
        return False, "Hook needs more concrete details"
    else:
        return False, "Hook lacks concrete, specific observations"
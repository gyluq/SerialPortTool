"""Highlight rules and the matching engine.

Matches only return ranges and colors; rendering is left to the caller, so the
matching logic can be fully tested without Qt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Rule:
    pattern: str
    color: str
    is_regex: bool = False
    enabled: bool = True
    regex: re.Pattern[str] | None = field(default=None, repr=False)


def compile_rule(rule: Rule) -> Rule:
    """Compile the regex rule. Invalid patterns do not raise; regex is just set to
    None, which disables the rule."""
    if rule.is_regex:
        try:
            rule.regex = re.compile(rule.pattern)
        except re.error:
            rule.regex = None
    else:
        rule.regex = None
    return rule


def compile_rules(rules: list[Rule]) -> list[Rule]:
    return [compile_rule(rule) for rule in rules]


def find_matches(text: str, rules: list[Rule]) -> list[tuple[int, int, str]]:
    """Return all matching ranges (start, end, color), ordered by rule."""
    matches: list[tuple[int, int, str]] = []
    if not text:
        return matches

    for rule in rules:
        if not rule.enabled or not rule.pattern:
            continue

        if rule.is_regex:
            if rule.regex is None:
                continue
            for match in rule.regex.finditer(text):
                if match.end() > match.start():
                    matches.append((match.start(), match.end(), rule.color))
        else:
            start = 0
            while True:
                index = text.find(rule.pattern, start)
                if index < 0:
                    break
                matches.append((index, index + len(rule.pattern), rule.color))
                start = index + len(rule.pattern)

    return matches

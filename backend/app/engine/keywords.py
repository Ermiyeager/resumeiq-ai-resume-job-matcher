"""Dictionary-based skill extraction.

Within each sentence, every alias of every skill is searched. Overlapping
matches are resolved longest-first, so "inbound customer calls" wins over
"calls", and "schedule appointments" wins over "schedule".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from .skills_dictionary import SKILLS, SKILLS_BY_NAME, SkillDef
from .text import normalize

# A skill mentioned in one of these contexts is not treated as confirmed.
_WEAK_CONTEXT = re.compile(
    r"\b(currently learning|learning|want to learn|plan to learn|interested in|familiar with|"
    r"exposure to|basic knowledge of|beginner|no experience|not experienced|aspiring|"
    r"hope to|would like to)\b"
)
WEAK_SECTIONS = {"interests"}


@dataclass
class RawHit:
    skill: SkillDef
    surface: str
    explicit: bool       # False for hint phrases
    start: int
    end: int


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[re.Pattern, SkillDef, bool]]:
    pats: list[tuple[re.Pattern, SkillDef, bool]] = []
    for skill in SKILLS:
        for alias in skill.all_aliases:
            pats.append((_compile(alias), skill, True))
        for hint in skill.hints:
            pats.append((_compile(hint), skill, False))
    return pats


def _compile(phrase: str) -> re.Pattern:
    body = r"[\s-]+".join(re.escape(word) for word in phrase.lower().split())
    return re.compile(rf"(?<![a-z0-9+#/]){body}(?![a-z0-9+#]|\.[a-z0-9])")


def find_skills(sentence: str) -> list[RawHit]:
    """All non-overlapping skill hits in one sentence, explicit hits preferred."""
    text = normalize(sentence)
    candidates: list[RawHit] = []
    for pattern, skill, explicit in _patterns():
        for m in pattern.finditer(text):
            candidates.append(RawHit(skill, m.group(0), explicit, m.start(), m.end()))
    # longest first; explicit before hint at equal length
    candidates.sort(key=lambda h: (-(h.end - h.start), not h.explicit))
    taken: list[RawHit] = []
    for hit in candidates:
        if all(hit.end <= t.start or hit.start >= t.end for t in taken):
            taken.append(hit)
    # a skill found explicitly makes its hint hits redundant
    explicit_names = {h.skill.name for h in taken if h.explicit}
    return [h for h in taken if h.explicit or h.skill.name not in explicit_names]


def is_weak_context(sentence: str, section: str) -> bool:
    return section in WEAK_SECTIONS or bool(_WEAK_CONTEXT.search(normalize(sentence)))


def implied_by(skill_name: str) -> list[str]:
    """Skills inferred from a confirmed skill, followed transitively."""
    seen: list[str] = []
    stack = list(SKILLS_BY_NAME[skill_name].implies)
    while stack:
        name = stack.pop()
        if name not in seen and name != skill_name:
            seen.append(name)
            stack.extend(SKILLS_BY_NAME[name].implies)
    return seen

"""Small, dependency-free text helpers shared by the engine."""

from __future__ import annotations

import re
import unicodedata

_BULLET_RE = re.compile(r"^\s*(?:[-*•▪◦●■►✓]+|\d+[.)])\s*")
_MARKDOWN_RE = re.compile(r"[#*_`]+")
_SPACE_RE = re.compile(r"[ \t\u00a0]+")


def normalize(text: str) -> str:
    """Lowercase, unify dashes/quotes and collapse whitespace (newlines are kept)."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub("[\u2010-\u2015]", "-", text)
    text = _SPACE_RE.sub(" ", text)
    return text.lower()


def clean_line(line: str) -> str:
    """Strip bullets and markdown decoration from a single line."""
    line = _BULLET_RE.sub("", line)
    line = _MARKDOWN_RE.sub("", line)
    return _SPACE_RE.sub(" ", line).strip()


def lines(text: str) -> list[str]:
    """Non-empty cleaned lines."""
    return [c for c in (clean_line(raw) for raw in text.splitlines()) if c]


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9])")


def sentences(text: str) -> list[str]:
    """Split text into sentence-sized units. Each line is at least one unit."""
    out: list[str] = []
    for line in lines(text):
        out.extend(part.strip() for part in _SENTENCE_SPLIT.split(line) if part.strip())
    return out


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9+#.]+", text))

"""Semantic similarity backends.

The engine asks one question: how similar is each text in A to each text in B?
Three backends answer it, picked automatically in this order:

1. Sentence Transformers (all-MiniLM-L6-v2): meaning-based embeddings.
2. TF-IDF over word and character n-grams (scikit-learn): lexical, fast.
3. Token overlap (pure Python): last-resort fallback for minimal installs.

Each backend has its own thresholds, because cosine scores from different
methods are not on the same scale. Similarity is only ever one signal: a high
score produces SEMANTIC_MATCH or NEEDS_VERIFICATION, never a confirmed skill.

Set RESUMEIQ_EMBEDDINGS=off to skip loading the transformer model.
"""

from __future__ import annotations

import math
import os
import re
from functools import lru_cache

_STOP = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "with", "on", "at", "by", "from", "as", "is",
    "are", "be", "was", "were", "that", "this", "it", "you", "your", "we", "our", "i", "my", "will", "can",
    "who", "when", "what", "if", "not", "all", "any", "have", "has", "had", "need", "needed", "using",
    "experience", "ability", "able", "strong", "good", "knowledge", "understanding", "work", "working",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9+#]+", text.lower()) if t not in _STOP and len(t) > 1]


def _stem(token: str) -> str:
    """Tiny suffix stripper so 'handled', 'handles' and 'handle' compare equal."""
    for suffix in ("ing", "ed", "es", "s", "ly"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    if token.endswith("e") and len(token) > 4:
        token = token[:-1]
    return token


class SimilarityBackend:
    name = "base"
    strong = 0.6   # at or above: SEMANTIC_MATCH / requirement COVERED
    weak = 0.45    # at or above: NEEDS_VERIFICATION / requirement PARTIAL

    def matrix(self, a: list[str], b: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError


class TokenOverlapBackend(SimilarityBackend):
    name = "token-overlap"
    strong = 0.5
    weak = 0.3

    def matrix(self, a, b):
        sa = [{_stem(t) for t in _tokens(x)} for x in a]
        sb = [{_stem(t) for t in _tokens(x)} for x in b]
        out = []
        for x in sa:
            row = []
            for y in sb:
                if not x or not y:
                    row.append(0.0)
                else:
                    # overlap coefficient normalised by the smaller set, damped by size difference
                    inter = len(x & y)
                    row.append(inter / math.sqrt(len(x) * len(y)))
            out.append(row)
        return out


class TfidfBackend(SimilarityBackend):
    name = "tfidf"
    # Calibrated on the fixtures in tests/: related sentences score ~0.3-0.5,
    # unrelated ones stay below ~0.1.
    strong = 0.30
    weak = 0.13

    def matrix(self, a, b):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        def prep(texts):
            return [" ".join(_stem(t) for t in _tokens(x)) for x in texts]

        pa, pb = prep(a), prep(b)
        corpus = pa + pb
        if not any(corpus):
            return [[0.0] * len(b) for _ in a]
        word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit(corpus)
        char = TfidfVectorizer(analyzer="char_wb", ngram_range=(4, 5), sublinear_tf=True).fit(corpus)
        sim_w = cosine_similarity(word.transform(pa), word.transform(pb))
        sim_c = cosine_similarity(char.transform(pa), char.transform(pb))
        combined = 0.6 * sim_w + 0.4 * sim_c
        return combined.tolist()


class SentenceTransformerBackend(SimilarityBackend):
    name = "sentence-transformers/all-MiniLM-L6-v2"
    strong = 0.6
    weak = 0.45

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.name = model_name

    def matrix(self, a, b):
        from sklearn.metrics.pairwise import cosine_similarity

        ea = self.model.encode(a, normalize_embeddings=True)
        eb = self.model.encode(b, normalize_embeddings=True)
        return cosine_similarity(ea, eb).tolist()


@lru_cache(maxsize=1)
def get_backend() -> SimilarityBackend:
    choice = os.getenv("RESUMEIQ_EMBEDDINGS", "auto").lower()
    if choice not in {"off", "tfidf", "tokens"}:
        try:
            return SentenceTransformerBackend()
        except Exception:
            pass
    if choice != "tokens":
        try:
            import sklearn  # noqa: F401

            return TfidfBackend()
        except ImportError:
            pass
    return TokenOverlapBackend()

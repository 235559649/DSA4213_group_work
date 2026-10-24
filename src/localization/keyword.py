"""BM25 lexical retrieval over repository index records.

Score each code entity separately, then assign each file its maximum
entity score. Return all positive-scoring files by default.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from src.repository.indexer import RepositoryIndex


def tokenize(text: str) -> list[str]:
    """Split text into lowercase searchable tokens (existing tokenizer)."""
    return re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*|\d+", text.lower())


class BM25Retriever:
    """Rank files by the highest BM25 score of their indexed entities."""

    def __init__(
        self,
        index: RepositoryIndex,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")

        self.index = index
        self.k1 = k1
        self.b = b

        # Each record is a separate BM25 document (not an entire file).
        self.documents: list[tuple[str, list[str]]] = []
        self.term_freqs: list[Counter[str]] = []
        self.doc_freqs: Counter[str] = Counter()

        for record in index.records:
            tokens = tokenize(record.retrieval_text or "")
            if not tokens:
                continue
            self.documents.append((record.path, tokens))
            self.term_freqs.append(Counter(tokens))
            self.doc_freqs.update(set(tokens))

        self.N = len(self.documents)
        self.avgdl = (
            sum(len(tokens) for _, tokens in self.documents) / self.N
            if self.N else 0.0
        )

    def score(self, query: str) -> dict[str, float]:
        """Return the maximum entity BM25 score for every indexed file."""
        if not self.N or not query.strip():
            return {}

        query_terms = set(tokenize(query))
        if not query_terms:
            return {}

        file_scores: dict[str, float] = {}
        for (path, tokens), freqs in zip(self.documents, self.term_freqs):
            dl = len(tokens)
            entity_score = 0.0
            for term in query_terms:
                tf = freqs[term]
                if not tf:
                    continue
                df = self.doc_freqs[term]
                idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * dl / self.avgdl
                )
                entity_score += idf * tf * (self.k1 + 1) / denominator

            file_scores[path] = max(file_scores.get(path, 0.0), entity_score)

        return file_scores

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[tuple[str, float]]:
        """Return positive-scoring files sorted by score, then path.

        top_k=None (default) returns the COMPLETE positive ranking.
        Pass top_k=5 or top_k=10 only when a downstream consumer needs it.
        """
        if top_k is not None and top_k < 0:
            raise ValueError("top_k must be nonnegative or None")

        ranked = sorted(
            ((path, score) for path, score in self.score(query).items() if score > 0),
            key=lambda item: (-item[1], item[0]),
        )
        return ranked if top_k is None else ranked[:top_k]

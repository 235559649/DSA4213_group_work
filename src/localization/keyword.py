"""BM25 lexical retrieval over repository index records."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from src.repository.indexer import RepositoryIndex


def tokenize(text: str) -> list[str]:
    """Split text into lowercase searchable tokens."""
    return re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*|\d+", text.lower())


class BM25Retriever:
    """Rank repository files using BM25."""

    def __init__(
        self,
        index: RepositoryIndex,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.index = index
        self.k1 = k1
        self.b = b

        self.documents = {}
        self.term_freqs = {}
        self.doc_freqs = Counter()

        # Combine retrieval text from all records belonging to each file.
        grouped = defaultdict(list)

        for record in index.records:
            grouped[record.path].append(record.retrieval_text)

        for path, texts in grouped.items():
            combined = " ".join(texts)
            tokens = tokenize(combined)

            self.documents[path] = tokens
            self.term_freqs[path] = Counter(tokens)

            for term in set(tokens):
                self.doc_freqs[term] += 1

        self.N = len(self.documents)

        self.avgdl = (
            sum(len(tokens) for tokens in self.documents.values()) / self.N
            if self.N > 0
            else 0
        )

    def score(self, query: str) -> dict[str, float]:
        """Calculate BM25 scores for all indexed files."""

        query_tokens = tokenize(query)
        scores = {}

        for path, tokens in self.documents.items():

            dl = len(tokens)
            score = 0.0

            for term in set(query_tokens):

                tf = self.term_freqs[path][term]

                if tf == 0:
                    continue

                df = self.doc_freqs[term]

                idf = math.log(
                    1 + (self.N - df + 0.5) / (df + 0.5)
                )

                denominator = (
                    tf
                    + self.k1
                    * (1 - self.b + self.b * dl / self.avgdl)
                )

                score += idf * (
                    tf * (self.k1 + 1) / denominator
                )

            scores[path] = score

        return scores

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Return top-k positive-scoring files."""

        scores = self.score(query)

        ranked = sorted(
            (
                (path, score)
                for path, score in scores.items()
                if score > 0
            ),
            key=lambda item: (-item[1], item[0]),
        )

        return ranked[:top_k]
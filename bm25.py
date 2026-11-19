"""A small BM25 keyword scorer, so exact terms like 'GST F5' are found reliably."""
import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(d)) for d in documents]       # term counts per doc
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / len(self.lengths)
        doc_freq = Counter(term for d in self.docs for term in d)    # docs containing term
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in doc_freq.items()}

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        result = []
        for counts, length in zip(self.docs, self.lengths):
            score = 0.0
            for t in terms:
                tf = counts.get(t, 0)
                if tf:
                    norm = tf + self.k1 * (1 - self.b + self.b * length / self.avg_len)
                    score += self.idf[t] * tf * (self.k1 + 1) / norm
            result.append(score)
        return result

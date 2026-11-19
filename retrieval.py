"""Hybrid retrieval: embeddings (meaning) + BM25 (exact words), then merge scores."""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from bm25 import BM25

INDEX_DIR = Path(__file__).parent / "index"


def _min_max(values) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    span = x.max() - x.min()
    return np.zeros_like(x) if span == 0 else (x - x.min()) / span


class Retriever:
    def __init__(self) -> None:
        meta = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
        self.chunks = meta["chunks"]
        self.vectors = np.load(INDEX_DIR / "embeddings.npy")
        self.model = SentenceTransformer(meta["model"])   # same model as ingest
        self.bm25 = BM25([c["text"] for c in self.chunks])

    def search(self, query: str, k: int = 5, alpha: float = 0.5) -> list[dict]:
        q = self.model.encode([query], normalize_embeddings=True)[0]
        dense = self.vectors @ q                            # cosine similarity
        sparse = self.bm25.scores(query)
        combined = alpha * _min_max(dense) + (1 - alpha) * _min_max(sparse)
        top = np.argsort(-combined)[:k]
        return [{**self.chunks[i], "score": round(float(combined[i]), 3)} for i in top]

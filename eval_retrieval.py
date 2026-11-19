"""Measure retrieval quality: recall@k and MRR on eval_questions.json."""
import json
import sys
from pathlib import Path

from retrieval import Retriever

K = 5


def main(alpha: float) -> None:
    questions = json.loads((Path(__file__).parent / "eval_questions.json").read_text())
    retriever = Retriever()
    hits, reciprocal_ranks, failures = 0, [], []
    for item in questions:
        sources = [r["source"] for r in retriever.search(item["question"], k=K, alpha=alpha)]
        if item["expected"] in sources:
            hits += 1
            reciprocal_ranks.append(1 / (sources.index(item["expected"]) + 1))
        else:
            reciprocal_ranks.append(0.0)
            failures.append((item["question"], sources[:3]))
    n = len(questions)
    print(f"alpha={alpha}  recall@{K} = {hits}/{n} = {hits / n:.2f}   "
          f"MRR = {sum(reciprocal_ranks) / n:.2f}")
    for question, got in failures:
        print(f"  MISS: {question!r} -> {got}")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.5)

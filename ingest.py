"""Read docs/*.md, split into chunks by heading, embed them, save to index/."""
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).parent
DOCS_DIR = BASE / "docs"
INDEX_DIR = BASE / "index"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"   # small, free, runs on a laptop
MAX_WORDS = 180                                          # long sections get split
OVERLAP = 30                                             # words shared between pieces


def split_by_headings(text: str):
    """Yield (heading_path, body) for every '## ' section of a markdown file."""
    title, heading, lines = "", "", []
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            if lines:
                yield f"{title} > {heading}", "\n".join(lines).strip()
            heading, lines = line[3:].strip(), []
        else:
            lines.append(line)
    if lines:
        yield f"{title} > {heading}", "\n".join(lines).strip()


def chunk_file(path: Path) -> list[dict]:
    chunks = []
    for heading, body in split_by_headings(path.read_text(encoding="utf-8")):
        words = body.split()
        if not words:
            continue
        for start in range(0, len(words), MAX_WORDS - OVERLAP):
            piece = " ".join(words[start:start + MAX_WORDS])
            chunks.append({
                "id": f"{path.stem}#{len(chunks)}",
                "source": path.name,
                "heading": heading,
                "text": f"{heading}\n{piece}",          # heading gives the chunk context
            })
            if start + MAX_WORDS >= len(words):
                break
    return chunks


def main() -> None:
    chunks = [c for path in sorted(DOCS_DIR.glob("*.md")) for c in chunk_file(path)]
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode([c["text"] for c in chunks], normalize_embeddings=True)
    INDEX_DIR.mkdir(exist_ok=True)
    np.save(INDEX_DIR / "embeddings.npy", vectors)
    meta = {"model": MODEL_NAME, "chunks": chunks}
    (INDEX_DIR / "chunks.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Indexed {len(chunks)} chunks from {len(list(DOCS_DIR.glob('*.md')))} files")


if __name__ == "__main__":
    main()

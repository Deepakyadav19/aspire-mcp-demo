"""Optional: full RAG in one script (retrieve, assemble prompt, generate with citations)."""
import os
import sys

from anthropic import Anthropic

from retrieval import Retriever

MODEL = os.environ.get("ASK_MODEL", "claude-haiku-5-5")
SYSTEM = (
    "You answer accounting questions for a small Singapore business. "
    "Use ONLY the sources provided. Cite sources inline like [gst-basics#2]. "
    "If the sources do not contain the answer, reply exactly: "
    "\"I don't know based on the documents.\""
)


def build_prompt(question: str, chunks: list[dict]) -> str:
    sources = "\n\n".join(f"[{c['id']}] {c['text']}" for c in chunks)
    return f"Sources:\n{sources}\n\nQuestion: {question}"


def main() -> None:
    question = " ".join(sys.argv[1:]) or "Can I claim GST on club subscription fees?"
    chunks = Retriever().search(question, k=5)
    client = Anthropic()                                 # reads ANTHROPIC_API_KEY
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_prompt(question, chunks)}],
    )
    print(response.content[0].text)
    print("\nRetrieved:", [c["id"] for c in chunks])


if __name__ == "__main__":
    main()

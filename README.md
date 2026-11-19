# aspire-mcp-demo

An MCP (Model Context Protocol) server that lets an AI assistant such as Claude Desktop
**query invoices** and **answer accounting questions from a document corpus** using
hybrid RAG (embeddings + BM25), with a small retrieval evaluation harness.

> Personal learning prototype built around an accounting-product use case
> (Singapore SME bookkeeping). All data is fake. Not affiliated with or endorsed by any company.

![Python](https://img.shields.io/badge/python-3.12-blue) ![MCP](https://img.shields.io/badge/MCP%20SDK-2.x-purple) ![License](https://img.shields.io/badge/license-MIT-green)

---

## What it does

Ask Claude things like:

- *"Which invoices are overdue, and how much is still open on each?"* → `list_invoices` + `get_invoice`
- *"Can I claim GST on club subscription fees?"* → `search_accounting_notes`, answer grounded in the notes with citations like `[gst-basics#2]`

```
┌──────────────────┐  JSON-RPC over stdio  ┌──────────────────────────────┐
│  Claude Desktop  │ ────────────────────▶ │  server.py (MCPServer)       │
│  (MCP host)      │ ◀──────────────────── │                              │
└──────────────────┘                       │  list_invoices ─┐            │
                                           │  get_invoice  ──┼─▶ SQLite   │  invoices.db (read-only)
                                           │                 │            │
                                           │  search_accounting_notes ─▶ Retriever
                                           └──────────────────────────────┘     │
                                                         ┌────────────────────────┴──────────┐
                                                         │ embeddings (all-MiniLM-L6-v2)      │
                                                         │   + BM25 keywords, min-max blend   │
                                                         │ index/ ← ingest.py ← docs/*.md     │
                                                         └────────────────────────────────────┘
```

## MCP tools

| Tool | Arguments | Returns |
|---|---|---|
| `list_invoices` | `status?` (DRAFT, ISSUED, PARTIALLY_PAID, PAID, VOID), `overdue_only?`, `limit` (1–50) | Invoices, newest first |
| `get_invoice` | `invoice_id` | One invoice plus `open_minor` (unpaid amount) |
| `search_accounting_notes` | `question`, `k` (1–8) | Top-k chunks with `id`, `heading`, `text`, `score` |

## Design decisions

- **Narrow, task-shaped tools, not `run_sql`.** The model can only do what the tools allow, and the descriptions double as API docs for the model.
- **Read-only by construction.** SQLite is opened with `mode=ro`; there are no write tools.
- **Bounded output.** `limit` is clamped to 50 and `k` to 8, so a single call can't flood the context window.
- **Money in integer minor units** (cents; JPY has 0 decimals), so there are no floating-point rounding errors.
- **Errors the model can act on.** Bad input raises `ToolError`, whose message goes back to the model (for example, the list of valid statuses).
- **stdout is the protocol.** All logging goes to stderr.
- **Hybrid retrieval.** Embeddings catch paraphrases ("Figma subscription" → software expenses); BM25 catches exact terms ("GST F5"). Scores are min-max normalized and blended with `alpha`.
- **Grounded answers.** The search tool's description tells the model to answer only from the returned chunks, cite chunk ids, and say "I don't know" when nothing relevant comes back.

## Project layout

| File | Purpose |
|---|---|
| `docs/*.md` | 5 accounting notes: GST, expense categories, month-end close, invoices & credit notes, FX gains/losses (the RAG corpus) |
| `seed.py` | Creates `invoices.db` with 40 deterministic fake invoices (SGD/USD/JPY) |
| `bm25.py` | Small dependency-free BM25 scorer |
| `ingest.py` | Heading-aware chunking (max 180 words, 30-word overlap) + embeddings → `index/` |
| `retrieval.py` | `Retriever`: hybrid dense + sparse search |
| `eval_questions.json` | 15 questions, each with its expected source document |
| `eval_retrieval.py` | Reports recall@5 and MRR for a given `alpha` |
| `server.py` | The MCP server (stdio transport) |
| `ask.py` | Optional: end-to-end RAG answer with the Claude API |

## Quick start

Requires [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you).

```bash
git clone https://github.com/<your-username>/aspire-mcp-demo.git
cd aspire-mcp-demo
uv sync                        # install dependencies

uv run seed.py                 # -> invoices.db (40 fake invoices)
uv run ingest.py               # -> index/ (18 chunks; downloads the embedding model once)
```

Test the tools in the browser with the MCP Inspector (needs Node.js 18+):

```bash
uv run mcp dev server.py
```

### Connect to Claude Desktop

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "aspirebooks-demo": {
      "command": "/absolute/path/to/uv",
      "args": ["--directory", "/absolute/path/to/aspire-mcp-demo", "run", "server.py"],
      "env": { "HF_HUB_OFFLINE": "1" }
    }
  }
}
```

Use `which uv` to find the uv path. `HF_HUB_OFFLINE=1` stops the server from calling Hugging Face at startup once the model is cached by `ingest.py`. Fully quit and reopen Claude Desktop, and the three tools appear under the tools menu.

### Optional: end-to-end RAG with the Claude API

```bash
ANTHROPIC_API_KEY=... uv run ask.py "Is a laptop an expense or a fixed asset?"
```

## Retrieval evaluation

```bash
uv run eval_retrieval.py 1.0   # embeddings only
uv run eval_retrieval.py 0.0   # BM25 keywords only
uv run eval_retrieval.py 0.5   # hybrid
```

Results with `all-MiniLM-L6-v2` (15 questions):

| Run | recall@5 | MRR | Misses |
|---|---|---|---|
| Embeddings only (`alpha=1.0`) | 15/15 | 1.00 | none |
| Keywords only (`alpha=0.0`) | 14/15 | 0.90 | "Figma subscription" (word not in the docs) |
| Hybrid (`alpha=0.5`) | 15/15 | 0.96 | none |

With `MAX_WORDS=40` (21 chunks) the results were the same apart from hybrid MRR at 0.95. The sections are already short, so this corpus is too small to show a chunking effect.

## Production path

What would change for a real multi-tenant accounting product:

- **Remote transport** (Streamable HTTP) with **OAuth**: each call runs as the signed-in user, so existing role permissions apply.
- **Call existing service APIs**, not the database: the MCP server stays a thin adapter.
- **Write tools create drafts only** (for example `create_invoice_draft`); issuing or paying stays a human action in the app.
- **Per-tool admin toggles and an audit log** of every tool call.
- **Vector store** (for example pgvector) instead of `.npy` files, a reranker, and a larger eval set run in CI.

## License

MIT

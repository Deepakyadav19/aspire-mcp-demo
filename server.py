"""MCP server: exposes invoices (SQLite) and accounting notes (RAG) as tools."""
import sqlite3
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError   # message reaches the model

from retrieval import Retriever

BASE = Path(__file__).parent
DB_PATH = BASE / "invoices.db"
TODAY = "2026-11-19"                      # fixed "today" so the demo data stays overdue
MAX_ROWS = 50
STATUSES = {"DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "VOID"}

mcp = MCPServer("aspirebooks-demo")
retriever = Retriever()                   # loads the index once, at startup


def log(message: str) -> None:
    print(message, file=sys.stderr)       # never print to stdout: it carries the protocol


def run_query(sql: str, params: list) -> list[dict]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)   # read-only connection
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@mcp.tool()
def list_invoices(status: str | None = None, overdue_only: bool = False,
                  limit: int = 20) -> list[dict]:
    """List invoices, newest first.

    status: one of DRAFT, ISSUED, PARTIALLY_PAID, PAID, VOID (optional).
    overdue_only: only unpaid invoices whose due date is before today (2026-11-19).
    limit: 1 to 50. Amounts are integer minor units (cents; JPY has no decimals).
    """
    limit = max(1, min(limit, MAX_ROWS))
    sql = ("SELECT id, number, customer, currency, total_minor, amount_paid_minor, "
           "status, due_date FROM invoice WHERE 1 = 1")
    params: list = []
    if status:
        status = status.upper()
        if status not in STATUSES:
            raise ToolError(f"status must be one of {sorted(STATUSES)}")
        sql += " AND status = ?"
        params.append(status)
    if overdue_only:
        sql += " AND status IN ('ISSUED', 'PARTIALLY_PAID') AND due_date < ?"
        params.append(TODAY)
    sql += " ORDER BY issue_date DESC LIMIT ?"
    params.append(limit)
    log(f"list_invoices status={status} overdue_only={overdue_only} limit={limit}")
    return run_query(sql, params)


@mcp.tool()
def get_invoice(invoice_id: int) -> dict:
    """Get one invoice by its numeric id, including the open (unpaid) amount."""
    rows = run_query("SELECT * FROM invoice WHERE id = ?", [invoice_id])
    if not rows:
        raise ToolError(f"No invoice with id {invoice_id}")
    invoice = rows[0]
    invoice["open_minor"] = invoice["total_minor"] - invoice["amount_paid_minor"]
    log(f"get_invoice id={invoice_id}")
    return invoice


@mcp.tool()
def search_accounting_notes(question: str, k: int = 5) -> list[dict]:
    """Search the company's accounting notes (GST, expense categories, month-end
    close, invoices, FX). Answer ONLY from the returned chunks and cite their ids,
    for example [gst-basics#2]. If nothing relevant is returned, say you don't know.
    """
    k = max(1, min(k, 8))
    results = retriever.search(question, k=k)
    log(f"search q={question!r} -> {[r['id'] for r in results]}")
    return [{"id": r["id"], "heading": r["heading"], "text": r["text"],
             "score": r["score"]} for r in results]


if __name__ == "__main__":
    mcp.run()                             # stdio transport by default

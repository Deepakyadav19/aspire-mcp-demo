"""Create invoices.db with 40 fake invoices for the demo."""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "invoices.db"
TODAY = date(2026, 11, 19)
CUSTOMERS = ["Kopi Corner Pte Ltd", "Lion City Logistics", "Marina Design Studio",
             "Orchard Tech", "Tiong Bahru Bakery"]
CURRENCIES = [("SGD", 2), ("USD", 2), ("JPY", 0)]          # (code, decimal places)
STATUSES = ["DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "VOID"]


def main() -> None:
    random.seed(42)                                         # same data on every run
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS invoice")
    conn.execute("""
        CREATE TABLE invoice (
            id                INTEGER PRIMARY KEY,
            number            TEXT UNIQUE,                  -- NULL while DRAFT
            customer          TEXT NOT NULL,
            currency          TEXT NOT NULL,
            total_minor       INTEGER NOT NULL,             -- money in minor units
            amount_paid_minor INTEGER NOT NULL,
            status            TEXT NOT NULL,
            issue_date        TEXT NOT NULL,
            due_date          TEXT NOT NULL
        )""")
    for i in range(1, 41):
        currency, decimals = random.choice(CURRENCIES)
        total = random.randint(100, 20_000) * 10 ** decimals
        status = random.choice(STATUSES)
        if status == "PAID":
            paid = total
        elif status == "PARTIALLY_PAID":
            paid = total // 2
        else:
            paid = 0
        issued = TODAY - timedelta(days=random.randint(0, 90))
        number = None if status == "DRAFT" else f"INV-2026-{i:04d}"
        conn.execute(
            "INSERT INTO invoice VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (i, number, random.choice(CUSTOMERS), currency, total, paid, status,
             issued.isoformat(), (issued + timedelta(days=30)).isoformat()),
        )
    conn.commit()
    conn.close()
    print(f"Seeded 40 invoices into {DB_PATH.name}")


if __name__ == "__main__":
    main()

"""Create the tables and the fictional customers. Safe to re-run.

    .venv/bin/python -m service.seed            # tables + customers
    .venv/bin/python -m service.seed --reset    # also clear jobs, metrics, incidents, approvals
"""

from __future__ import annotations

import argparse

from common import db

# Fictional demo customers (spec: synthetic data only). Price is per job, for "estimated value waiting".
CUSTOMERS = [
    ("CUST-NORTHWIND", "Northwind Analytics", "Gold", 4.00),
    ("CUST-BLUEFIN", "Bluefin Health", "Silver", 2.50),
    ("CUST-ACORN", "Acorn Retail", "Bronze", 1.00),
]
PRICE = {cid: price for cid, _, _, price in CUSTOMERS}


def seed(reset: bool = False) -> None:
    conn = db.connect()
    conn.executemany(
        """INSERT INTO customers (id, name, tier)
           VALUES (?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             name = excluded.name,
             tier = excluded.tier""",
        [(cid, name, tier) for cid, name, tier, _ in CUSTOMERS],
    )
    if reset:
        for table in ("approvals", "incidents", "metrics", "jobs"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'jobs'")
    conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()
    seed(reset=args.reset)
    print(f"seeded {len(CUSTOMERS)} customers" + (" and cleared runtime tables" if args.reset else ""))

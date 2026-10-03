"""The shared SQLite database (timeline.md section 1: database tables).

Times are unix seconds (float). IDs that appear in chat messages are readable strings
(INC-0001, APR-0001); job IDs are integers.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from common import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
  id    TEXT PRIMARY KEY,
  name  TEXT NOT NULL,
  tier  TEXT NOT NULL CHECK (tier IN ('Gold', 'Silver', 'Bronze'))
);

CREATE TABLE IF NOT EXISTS jobs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id  TEXT NOT NULL REFERENCES customers(id),
  created_at   REAL NOT NULL,
  started_at   REAL,
  finished_at  REAL,
  status       TEXT NOT NULL CHECK (status IN ('pending', 'running', 'done')),
  price        REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_by_status ON jobs(status, created_at);

CREATE TABLE IF NOT EXISTS metrics (
  ts              REAL PRIMARY KEY,
  mem_used_gb     REAL,
  mem_avail_gb    REAL,
  gpu_util        REAL,
  service_status  TEXT,
  jobs_per_min    REAL
);

CREATE TABLE IF NOT EXISTS incidents (
  id           TEXT PRIMARY KEY,
  opened_at    REAL NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('open', 'awaiting_approval', 'resolved', 'unresolved')),
  trigger      TEXT NOT NULL,   -- JSON: what crossed the threshold
  report_json  TEXT             -- JSON: final report from the agent
);

CREATE TABLE IF NOT EXISTS approvals (
  id           TEXT PRIMARY KEY,
  incident_id  TEXT NOT NULL REFERENCES incidents(id),
  action       TEXT NOT NULL,
  target       TEXT NOT NULL,
  code_hash    TEXT NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'denied', 'expired')),
  created_at   REAL NOT NULL,
  decided_at   REAL,
  attempts     INTEGER NOT NULL DEFAULT 0
);
"""

OPEN_STATUSES = ("open", "awaiting_approval")


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open the database (creating tables if needed). Rows behave like dicts."""
    path = Path(path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(SCHEMA)
    return conn


def next_id(conn: sqlite3.Connection, table: str, prefix: str) -> str:
    """INC-0001, APR-0001, ... (table is a fixed internal name, never user input)."""
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] + 1
    return f"{prefix}-{n:04d}"


def open_incident(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM incidents WHERE status IN (?, ?) ORDER BY opened_at DESC LIMIT 1",
        OPEN_STATUSES,
    ).fetchone()

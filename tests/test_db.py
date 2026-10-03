"""Regression tests for the shared SQLite connection."""

import sqlite3

import pytest

from conftest import add_job
from service.seed import seed


def test_foreign_keys_are_enforced(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO jobs
               (customer_id, created_at, status, price)
               VALUES ('CUST-DOES-NOT-EXIST', 1, 'pending', 1)"""
        )


def test_seed_is_idempotent_without_deleting_existing_jobs(conn):
    add_job(conn, "CUST-NORTHWIND", created_at=1)
    seed()
    seed()

    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1

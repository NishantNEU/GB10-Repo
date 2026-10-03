"""Impact numbers must match a hand count exactly (timeline: Data Engineer, 15:30-16:00)."""

from conftest import add_job

from service import impact

NOW = 1_000_000.0


def test_hand_counted_fixture(conn):
    # delayed (pending > 30 s): 2 Northwind, 1 Acorn
    add_job(conn, "CUST-NORTHWIND", NOW - 90)
    add_job(conn, "CUST-NORTHWIND", NOW - 45)
    add_job(conn, "CUST-ACORN", NOW - 31)
    # not delayed: pending 10 s, done long ago
    add_job(conn, "CUST-BLUEFIN", NOW - 10)
    add_job(conn, "CUST-BLUEFIN", NOW - 500, status="done", started_at=NOW - 400)
    # running: waited 40 s before starting -> delayed; waited 5 s -> not delayed
    add_job(conn, "CUST-BLUEFIN", NOW - 60, status="running", started_at=NOW - 20)
    add_job(conn, "CUST-ACORN", NOW - 8, status="running", started_at=NOW - 3)

    r = impact.compute(conn, now=NOW, threshold_s=30)

    assert r["delayed_jobs"] == 4
    assert r["affected_customers"] == 3
    assert r["longest_wait_s"] == 90.0 and r["longest_wait"] == "1m 30s"
    assert r["backlog"] == 6                              # every pending + running job
    assert r["estimated_value"] == 4.0 + 4.0 + 1.0 + 2.5  # prices of the 4 delayed jobs
    assert [c["id"] for c in r["customers"]] == ["CUST-NORTHWIND", "CUST-BLUEFIN", "CUST-ACORN"]  # tier order


def test_empty_queue(conn):
    r = impact.compute(conn, now=NOW)
    assert (r["delayed_jobs"], r["affected_customers"], r["backlog"], r["estimated_value"]) == (0, 0, 0, 0)

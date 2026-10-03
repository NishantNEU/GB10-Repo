"""Read-only check of the running GB10 tool server.

    .venv/bin/python -m toolserver.smoke
    .venv/bin/python -m toolserver.smoke --expect-hog

The second command is for use after chaos/start_hog.sh has started. It does not
request approval or stop a container.
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


PATHS = ("/incidents/current", "/metrics", "/processes/top?n=5", "/logs/service?lines=5",
         "/queue/status", "/impact", "/health")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Pitcrew's live read endpoints")
    parser.add_argument("--base", default="http://127.0.0.1:9000", help="tool server URL")
    parser.add_argument("--expect-hog", action="store_true", help="require pitcrew-test-hog in process evidence")
    args = parser.parse_args()

    results = {}
    for path in PATHS:
        try:
            with urlopen(args.base.rstrip("/") + path, timeout=5) as response:
                data = json.load(response)
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            return 1
        results[path.split("?")[0]] = data
        print(f"OK   {path}")

    processes = results["/processes/top"].get("processes", [])
    if args.expect_hog and not any(p.get("container") == "pitcrew-test-hog" for p in processes):
        print("FAIL pitcrew-test-hog is absent from /processes/top", file=sys.stderr)
        return 1

    incident = results["/incidents/current"]
    health = results["/health"]
    impact = results["/impact"]
    print(f"Incident: {incident.get('id') or 'none'} ({incident.get('status', 'unknown')})")
    print(f"Health: {health.get('status', 'unknown')}; jobs/min: {health.get('jobs_per_min', '?')}")
    print(f"Impact: {impact.get('delayed_jobs', '?')} delayed jobs, "
          f"{impact.get('affected_customers', '?')} affected customers")
    print("Test container: " + ("visible" if any(p.get("container") == "pitcrew-test-hog"
                                              for p in processes) else "absent"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

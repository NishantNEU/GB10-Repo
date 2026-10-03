"""Local presenter UI with a read-only view of the GB10 toolserver.

The guided incident is a scripted demo in the browser. This server never calls
the toolserver's approval, report, or Docker action endpoints.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

STATIC = Path(__file__).parent / "static"
TOOLSERVER_URL = os.environ.get("PITCREW_TOOLSERVER_URL", "http://127.0.0.1:9000").rstrip("/")
READ_ENDPOINTS = {
    "incident": "/incidents/current",
    "health": "/health",
    "metrics": "/metrics",
    "queue": "/queue/status",
    "impact": "/impact",
    "processes": "/processes/top?n=5",
    "logs": "/logs/service?lines=18",
}

app = FastAPI(title="Pitcrew Demo Console", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/api/live")
async def live_snapshot() -> JSONResponse:
    """Collect only GET evidence. A stopped toolserver leaves the replay usable."""

    async with httpx.AsyncClient(timeout=2.5, trust_env=False) as client:
        async def read(path: str) -> dict | None:
            try:
                response = await client.get(f"{TOOLSERVER_URL}{path}")
                response.raise_for_status()
                value = response.json()
                return value if isinstance(value, dict) else None
            except (httpx.HTTPError, ValueError):
                return None

        results = await asyncio.gather(*(read(path) for path in READ_ENDPOINTS.values()))

    data = dict(zip(READ_ENDPOINTS, results, strict=True))
    available = sum(value is not None for value in data.values())
    payload = {
        "source": "GB10 toolserver (read-only)",
        "sampled_at": datetime.now(timezone.utc).isoformat(),
        "connected": available > 0,
        "complete": available == len(READ_ENDPOINTS),
        "available_endpoints": available,
        "total_endpoints": len(READ_ENDPOINTS),
        "data": data,
    }
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Pitcrew presenter dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()

"""Settings shared by service/, toolserver/, skills/ and scripts/. Values come from .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else REPO / p


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


# Ports and names (timeline.md section 1: shared contracts)
TOOLSERVER_HOST = os.environ.get("TOOLSERVER_HOST", "0.0.0.0")
TOOLSERVER_PORT = int(os.environ.get("TOOLSERVER_PORT", "9000"))
VLLM_PORT = int(os.environ.get("VLLM_PORT", "8000"))
DB_PATH = _path(os.environ.get("PITCREW_DB", "data/pitcrew.db"))
HOG_CONTAINER = os.environ.get("HOG_CONTAINER", "pitcrew-test-hog")
HOG_LABEL = "pitcrew.role=test-hog"  # set by chaos/start_hog.sh; the stop action checks it

# Files the sample service writes and the tool server reads
LOG_DIR = REPO / "logs"
RUN_DIR = REPO / "run"
SERVICE_LOG = LOG_DIR / "service.log"
SERVICE_STATUS_FILE = RUN_DIR / "service_status.json"
SERVICE_STATUS_STALE_S = 10  # no heartbeat for this long means "down"

# Sample service behavior (Data Engineer)
JOB_INTERVAL_S = _float("JOB_INTERVAL_S", 2.0)        # a new job every ~2 s
JOB_TIME_HEALTHY_S = _float("JOB_TIME_HEALTHY_S", 1.5)
JOB_TIME_DEGRADED_S = _float("JOB_TIME_DEGRADED_S", 6.0)
# Degraded when host available memory drops below this. Calibrate from `free -h` with vLLM loaded.
MEM_THRESHOLD_GB = _float("MEM_THRESHOLD_GB", 30.0)

# Impact and detection (Data Engineer)
DELAY_THRESHOLD_S = _float("DELAY_THRESHOLD_S", 30.0)  # a job is "delayed" after waiting this long
INCIDENT_MIN_DELAYED = int(os.environ.get("INCIDENT_MIN_DELAYED", "5"))
DETECTOR_INTERVAL_S = _float("DETECTOR_INTERVAL_S", 5.0)

# Approvals (Backend)
APPROVER_BOT_TOKEN = os.environ.get("APPROVER_BOT_TOKEN", "")
ONCALL_CHAT_ID = os.environ.get("ONCALL_CHAT_ID", "")
APPROVAL_TTL_S = int(os.environ.get("APPROVAL_TTL_S", "300"))  # codes expire after 5 min
APPROVAL_MAX_ATTEMPTS = int(os.environ.get("APPROVAL_MAX_ATTEMPTS", "3"))

# Tool server serves fixed JSON when set (lets Kunal test the agent before the real data exists)
TOOLSERVER_STUB = os.environ.get("TOOLSERVER_STUB", "0") == "1"

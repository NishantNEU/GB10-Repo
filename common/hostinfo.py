"""Machine measurements, shared so the detector and the tool server report the same numbers."""

from __future__ import annotations

import json
import subprocess
import time

import psutil

from common import config

GB = 1024 ** 3


def memory() -> dict:
    vm = psutil.virtual_memory()
    return {
        "mem_total_gb": round(vm.total / GB, 1),
        "mem_used_gb": round((vm.total - vm.available) / GB, 1),
        "mem_avail_gb": round(vm.available / GB, 1),
        "mem_used_pct": round(100 * (vm.total - vm.available) / vm.total, 1),
    }


def gpu() -> dict:
    """GPU utilization and temperature from nvidia-smi; None where GB10 reports [N/A]."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip().splitlines()[0]
        name, util, temp = (x.strip() for x in out.split(","))
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        return {"gpu_name": None, "gpu_util": None, "gpu_temp_c": None}

    def num(v: str) -> float | None:
        try:
            return float(v)
        except ValueError:
            return None

    return {"gpu_name": name, "gpu_util": num(util), "gpu_temp_c": num(temp)}


def service_status() -> dict:
    """The sample service's own heartbeat (written every loop). Stale or missing = down."""
    try:
        data = json.loads(config.SERVICE_STATUS_FILE.read_text())
    except (OSError, ValueError):
        return {"status": "down", "reason": "no heartbeat file"}
    age = time.time() - data.get("ts", 0)
    if age > config.SERVICE_STATUS_STALE_S:
        return {**data, "status": "down", "reason": f"heartbeat {age:.0f}s old"}
    return data

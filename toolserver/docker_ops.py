"""Docker helpers: container names for processes, and stopping the test container.

Kept separate so tests can replace these functions without a Docker daemon.
"""

from __future__ import annotations

import re
import subprocess

from common import config

_CGROUP_ID = re.compile(r"([0-9a-f]{64})")
_MEMORY = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGT]?i?B)\b", re.I)


def _docker(*args: str, timeout: float = 15) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def container_names() -> dict[str, str]:
    """Full container ID -> name, for running containers. Empty if Docker isn't reachable."""
    try:
        r = _docker("ps", "--no-trunc", "--format", "{{.ID}} {{.Names}}", timeout=5)
    except (OSError, subprocess.SubprocessError):
        return {}
    return dict(line.split(" ", 1) for line in r.stdout.splitlines() if " " in line)


def container_of(pid: int, names: dict[str, str]) -> str | None:
    """Which container a host PID runs in, from its cgroup path (docker-<id>.scope)."""
    try:
        with open(f"/proc/{pid}/cgroup") as f:
            m = _CGROUP_ID.search(f.read())
    except OSError:
        return None
    return names.get(m.group(1)) if m else None


def container_memory() -> list[dict]:
    """Running containers with current memory use, even when host cgroups hide names."""
    try:
        result = _docker("stats", "--no-stream", "--format", "{{.Name}}|{{.MemUsage}}", timeout=8)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []

    units = {"B": 1, "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3,
             "TB": 1000 ** 4, "KIB": 1024, "MIB": 1024 ** 2,
             "GIB": 1024 ** 3, "TIB": 1024 ** 4}
    containers = []
    for line in result.stdout.splitlines():
        name, separator, usage = line.partition("|")
        match = _MEMORY.match(usage) if separator else None
        if not name or not match:
            continue
        memory_gb = float(match.group(1)) * units[match.group(2).upper()] / (1024 ** 3)
        containers.append({"pid": None, "name": "docker container", "rss_gb": round(memory_gb, 1),
                           "container": name, "source": "docker_stats"})
    return containers


def is_test_container(name: str) -> bool:
    """True only for the chaos container: right name AND the label start_hog.sh sets."""
    if name != config.HOG_CONTAINER:
        return False
    key, value = config.HOG_LABEL.split("=", 1)
    r = _docker("inspect", "--format", f'{{{{index .Config.Labels "{key}"}}}}', name, timeout=5)
    return r.returncode == 0 and r.stdout.strip() == value


def stop_container(name: str) -> tuple[bool, str]:
    r = _docker("stop", "-t", "5", name, timeout=30)
    return r.returncode == 0, (r.stdout or r.stderr).strip()

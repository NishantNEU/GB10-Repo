"""Docker helpers: container names for processes, and stopping the test container.

Kept separate so tests can replace these functions without a Docker daemon.
"""

from __future__ import annotations

import re
import subprocess

from common import config

_CGROUP_ID = re.compile(r"([0-9a-f]{64})")


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

"""Pitcrew test program: grows real resident memory in steps, then holds.

Runs inside the `pitcrew-test-hog` container (see start_hog.sh). Stdlib only.
Bounded three ways: --max-gb, the container's --memory limit, and --min-free-gb
(it stops growing before host MemAvailable drops below that floor).
"""

import argparse
import signal
import sys
import time

GIB = 1 << 30


def host_mem_available_gib() -> float:
    # Without lxcfs, /proc/meminfo inside a container reports the host's memory.
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024 / GIB
    raise RuntimeError("MemAvailable missing from /proc/meminfo")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--step-gb", type=float, default=1.0)
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--max-gb", type=float, default=30.0)
    p.add_argument("--min-free-gb", type=float, default=16.0)
    a = p.parse_args()

    # PID 1 ignores SIGTERM unless a handler is installed; exit fast on `docker stop`.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    step = int(a.step_gb * GIB)
    chunks = []
    print(f"hog: start step={a.step_gb}GiB every {a.interval}s max={a.max_gb}GiB "
          f"floor={a.min_free_gb}GiB avail={host_mem_available_gib():.1f}GiB", flush=True)

    while len(chunks) * a.step_gb < a.max_gb:
        avail = host_mem_available_gib()
        if avail - a.step_gb < a.min_free_gb:
            print(f"hog: floor reached avail={avail:.1f}GiB, holding", flush=True)
            break
        # Filled bytes, not bytearray(n): calloc'd zero pages would not become resident.
        chunks.append(b"\x01" * step)
        print(f"hog: held={len(chunks) * a.step_gb:.1f}GiB avail={host_mem_available_gib():.1f}GiB",
              flush=True)
        time.sleep(a.interval)

    print(f"hog: holding {len(chunks) * a.step_gb:.1f}GiB", flush=True)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    sys.exit(main())

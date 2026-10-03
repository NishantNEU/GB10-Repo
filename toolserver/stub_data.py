"""Fixed responses for TOOLSERVER_STUB=1, so the agent can be tested before real data exists.
Shapes match the real endpoints exactly."""

STUB = {
    "incidents_current": {
        "id": "INC-0001", "status": "open", "opened_at": "14:06:10", "age_s": 42.0,
        "trigger": {"rule": "delayed_jobs >= 5", "delayed_jobs": 7, "affected_customers": 3,
                    "longest_wait": "48s", "service_status": "degraded",
                    "mem_avail_gb": 14.2, "mem_used_gb": 107.4},
        "pending_approval_id": None,
    },
    "metrics": {"mem_total_gb": 121.6, "mem_used_gb": 107.4, "mem_avail_gb": 14.2, "mem_used_pct": 88.3,
                "gpu_name": "NVIDIA GB10", "gpu_util": 3.0, "gpu_temp_c": 48.0},
    "processes_top": {"processes": [
        {"pid": 41270, "name": "python3", "rss_gb": 28.0, "container": "pitcrew-test-hog"},
        {"pid": 30211, "name": "python3", "rss_gb": 22.6, "container": "pitcrew-vllm"},
        {"pid": 1882, "name": "gnome-shell", "rss_gb": 0.4, "container": None},
    ]},
    "logs": {"lines": [
        "2026-10-03 14:05:31 WARNING memory pressure: reducing throughput (available 29.4 GB < 30.0 GB)",
        "2026-10-03 14:05:37 WARNING job_done id=181 customer=CUST-NORTHWIND wait_s=12.3 run_s=6.0 mode=degraded",
    ]},
    "queue_status": {"pending": 9, "running": 1, "jobs_per_min": 10.0, "oldest_wait_s": 48.0},
    "impact": {"delayed_jobs": 7, "affected_customers": 3, "longest_wait": "48s", "longest_wait_s": 48.0,
               "backlog": 10, "estimated_value": 19.5,
               "estimated_value_label": "estimated billable work waiting (not lost revenue)",
               "delay_threshold_s": 30.0, "customers": [], "computed_at": 0},
    "health": {"status": "degraded", "jobs_per_min": 10.0, "mem_avail_gb": 14.2},
}

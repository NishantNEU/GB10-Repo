# Pitcrew presenter dashboard

This is a guided, browser-based hackathon demo. It walks through one memory-pressure incident: detection, an evidence trail, a verdict, simulated Slack approval, simulated Jira ticket, illustrative Git diff, simulated branch and tests, and a stable end state.

The incident journey is deliberately replayable. Its controls **do not** send Slack messages, create Jira issues, change Git branches, run tests, or stop containers. The separate **Live GB10** panel reads seven existing toolserver GET endpoints and shows real host/service evidence when the toolserver is running. It does not call mutation endpoints.

## Run

From the repository root:

```bash
.venv/bin/python -m dashboard.server
```

Open <http://127.0.0.1:8787> on the same machine. The default bind address is loopback, so the page is meant for the GB10's attached monitor. To use another local port, add `--port 8788`.

The live feed expects the existing toolserver at `http://127.0.0.1:9000`. Override it only if needed:

```bash
PITCREW_TOOLSERVER_URL=http://127.0.0.1:9000 .venv/bin/python -m dashboard.server
```

The page still works if the toolserver is unavailable. The main pulse and workflow always show the replayed scenario. The **Live GB10** switch changes the right-side telemetry panel and lower service-log panel only, so live measurements cannot be confused with the scripted outcome. Reset from the top bar or the page header between demos.

## Presenter path

1. **Simulate memory spike** — opens a sample incident and updates the system pulse.
2. **Bug identified · analyze** — replays six short, evidence-based checks. These are visible tool observations and conclusions, not hidden model reasoning.
3. **Send approval to Slack** — adds a simulated request to the Slack panel.
4. **Approve in Slack** — replays the guarded mitigation, recovery, and automatic Jira ticket creation. Deny shows that no action occurs.
5. **Review proposed fix** — shows an illustrative Git-style diff for the controlled test workload.
6. **Create demo branch**, **Run replayed tests**, **Mark stable & close ticket** — completes the prevention and verification story.

When presenting, describe the backend/Docker safety test as **real GB10 work that was separately validated**, and this page as the **scripted product workflow**. The interface labels simulated and live content separately throughout.

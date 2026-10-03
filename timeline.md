Pitcrew — 3.5-Hour Build Plan

Window: 14:30 → 18:00 code freeze (video, repo, writeup and NVIDIA hardware answers are all due at 18:00) After: 18:00–19:00 slides (everyone) · return the GB10 by 19:00 · 19:30 pitch if top 8 Base document: the latest Pitcrew spec, with the corrections below. This plan replaces the older team overview.

    The one goal: a single recorded incident, start to finish: healthy → test program causes slowdown → Pitcrew detects it → investigates → impact numbers → approval in Telegram → stops only the test program → verifies recovery → report. Anything that doesn't serve this sequence waits until it works.

0. Corrections to the spec (agreed)
Spec says 	Correct version
Prepare a live demo; the video is a backup 	No live demos (Rule 4). The video, embedded in the slides, is the demo. The GB10 is returned before the pitch
Acceptance: "a teammate can run it live" 	The full sequence is recorded end to end with narration and embedded in the deck
"Use whatever model runs" 	Qwen3.6-35B-A3B NVFP4 on a self-run vLLM from the kit (0.5 memory / 64K context). Fallback: Qwen3.5 9B on Ollama
Channel: Slack, Discord or Telegram 	Telegram
Duplicate headings for sections 14 and 15 	Renumber: 14 Judging · 15 Pitch · 16 Team decision
1. Shared contracts (agree on these in the first 10 minutes, then don't change them)
Ports and names
Thing 	Value
vLLM (model API) 	localhost:8000, blocked from the venue network
Pitcrew tool server 	0.0.0.0:9000 on the GB10 host, blocked from the venue network
Database 	~/GB10-Repo/data/pitcrew.db (SQLite, WAL mode)
Test program 	Docker container named pitcrew-test-hog (the only thing the agent may ever stop)
Secrets 	.env (git-ignored): APPROVER_BOT_TOKEN, ONCALL_CHAT_ID
Repo layout (each person owns one folder, which avoids merge conflicts)
Folder 	Owner
service/ (sample AI service, queue, detector, impact calculation) 	Data Engineer
toolserver/ (FastAPI tool server, approvals, incidents) 	Backend
skills/pitcrew/ (agent instructions, message templates) 	Kunal
chaos/, scripts/ (test program, reset, setup notes) 	Hardware Expert

Working on one GB10: each person keeps their own clone (~/dev/<name>/GB10-Repo) over VS Code Remote-SSH. ~/GB10-Repo is the integration copy where everything actually runs. Pull into it at each checkpoint.
Database tables
Table 	Columns
customers 	id, name, tier
jobs 	id, customer_id, created_at, started_at, finished_at, status (pending/running/done), price
metrics 	ts, mem_used_gb, mem_avail_gb, gpu_util, service_status, jobs_per_min
incidents 	id, opened_at, status (open/awaiting_approval/resolved/unresolved), trigger, report_json
approvals 	id, incident_id, action, target, code_hash, status (pending/approved/denied/expired), created_at, decided_at
Tool server endpoints (what the agent calls)
Endpoint 	Returns / does 	Risk
GET /incidents/current 	Open incident + trigger evidence 	Read
GET /metrics 	Memory used/available, GPU utilization, temperature 	Read
GET /processes/top?n=5 	Top memory users, including container names 	Read
GET /logs/service?lines=50 	Sample service log tail 	Read
GET /queue/status 	Pending jobs, jobs/min, oldest wait 	Read
GET /impact 	Calculated in code: delayed jobs, affected customers, longest wait, backlog, estimated value waiting 	Read
GET /health 	healthy / degraded / down + throughput 	Read
POST /approvals {incident_id, action, target, reason} 	Creates the approval and sends a one-time code to the on-call engineer's phone 	Safe
POST /approvals/{id}/deny 	Marks it denied; no action taken 	Safe
POST /actions/stop_test_program {approval_id, code} 	Checks code, expiry (5 min) and target == pitcrew-test-hog, then runs docker stop 	Approval required
POST /incidents/{id}/report 	Saves the final report and marks the incident resolved/unresolved 	Safe
How approval can't be faked

The agent never sees the approval code. The tool server sends it directly to the on-call engineer through a separate Telegram bot (the "Pitcrew Approvals" bot). The engineer types approve 4821 to the Pitcrew agent, and the agent passes the code to the tool server, which checks it. If the code doesn't match, nothing happens. This is our safety story on camera.
2. Who does what
Hardware Expert: model, platform, test program, recording
Time 	Task 	Done when
14:30–15:00 	Finish vLLM from the kit (0.5 / 64K), pass the tool-calling curl test, block ports 8000 and 9000 from the venue network 	curl localhost:8000/v1/models shows max_model_len: 65536; tool-call test returns get_metrics
15:00–15:20 	nemoclaw onboard → Local vLLM; connect Telegram with the Pitcrew bot token 	The agent replies to a Telegram message using local Qwen
15:20–15:45 	OpenShell network rules: allow only the host tool server (:9000) and api.telegram.org 	The agent can curl the tool server; anything else is blocked
15:45–16:15 	chaos/start_hog.sh: runs pitcrew-test-hog with --memory=32g, using the kit's vLLM image with --entrypoint python3 (no download), allocating ~1 GB every 3 s up to 30 GB 	Starting it drops host available memory by ~30 GB in about 90 s; it can't freeze the box
16:15–16:45 	scripts/reset.sh: removes the hog, reseeds the queue, clears incidents and approvals, restarts the sample service 	One command returns the system to "healthy" in under 60 s
16:45–17:15 	Set up recording: GNOME screen recorder on the GB10 + phone screen recording for Telegram; rehearse the shot list (Section 4) 	Test clip recorded and plays back
17:15–17:50 	Recording lead 	Final clip saved in 08_demo_backup/ and uploaded

Fallback: if NemoClaw onboarding isn't answering in Telegram by 15:20, move straight to plain OpenClaw pointed at the same vLLM, and tell the team.
Data Engineer: sample service, queue, detector, impact
Time 	Task 	Done when
14:30–14:45 	Create the DB tables (Section 1); seed 3 fictional customers (tiers Gold/Silver/Bronze) 	sqlite3 data/pitcrew.db .tables lists all five
14:45–15:30 	service/sample_service.py: adds a job every ~2 s across the customers. The worker processes one job per ~1.5 s. If host available memory < MEM_THRESHOLD_GB, it switches to degraded mode (~6 s per job) and logs WARN memory pressure: reducing throughput 	Runs healthy with a flat queue; forcing degraded mode makes the queue grow
15:30–16:00 	service/impact.py: delayed jobs (wait > 30 s), affected customers, longest wait, backlog, estimated value (price × delayed jobs, labeled "estimated billable work waiting") 	Numbers match a hand count on the seeded data
16:00–16:30 	service/detector.py: every 5 s, writes metrics; if ≥ 5 delayed jobs, opens one incident and calls the trigger (Section 3) 	Starting the hog opens exactly one incident within ~60 s
16:30–17:15 	Set MEM_THRESHOLD_GB from the real baseline (free -h with vLLM loaded); run the flow 3× with reset.sh 	Same counts each run
17:15–17:50 	Run the flow during recording (trigger + reset) 	—
Backend: tool server, approvals, incidents
Time 	Task 	Done when
14:30–14:45 	Create the Pitcrew Approvals bot in BotFather; the on-call engineer sends it /start; get ONCALL_CHAT_ID; put both in .env 	Test message arrives on the engineer's phone
14:45–15:15 	Stub tool server: every read endpoint returns fixed JSON, so Kunal can start testing immediately 	curl localhost:9000/metrics returns JSON
15:15–16:00 	Real read endpoints: psutil for metrics and processes, docker ps/stats for container names, DB queries for queue, impact (import from service/impact.py) and health 	Values change when the hog runs
16:00–16:30 	Approvals + stop action: 4-digit code → store a hash → send via the Approvals bot; stop checks code, expiry and target; deny endpoint 	Wrong code → refused; right code → only pitcrew-test-hog stops
16:30–17:15 	Report endpoint, GET /incidents/current, end-to-end fixes with the team 	Full flow passes once
17:15–17:50 	Plays the on-call engineer during recording (phone approval) 	—

Optional dashboard: only if the full flow passes by 16:45. Otherwise skip it; the Telegram thread and terminal are enough for the video.
Kunal: agent behavior, trigger, writeup
Time 	Task 	Done when
14:30–15:15 	Trigger test (highest risk, 45 min max). Find how a script can start the agent with no human message. Try in order: ① an OpenClaw gateway webhook/hook, ② an OpenClaw CLI command that sends a message to the agent (check --help inside the sandbox), ③ fallback: OpenClaw's scheduled heartbeat/cron every 1 min that calls GET /incidents/current 	A script or schedule makes the agent post in Telegram with no one typing. Tell the team which option won
15:15–16:00 	skills/pitcrew/SKILL.md: what Pitcrew is; the endpoints with curl examples; the investigation order (incident → metrics → top processes → logs → queue → impact); the structured diagnosis (cause, evidence, uncertainty, proposed action, impact, next check) 	Against the stub server, the agent calls the tools in order and gives a structured diagnosis
16:00–16:30 	Approval and verification behavior: request approval → ask the human for the code → on approve <code> call stop → wait 20 s → check /health and /queue/status → report; on deny, call deny and report "no action taken" 	Both approve and deny paths work
16:30–17:15 	Rules + message polish: never run any command other than curl to :9000; never state a number that didn't come from /impact; say "unresolved" if recovery isn't verified; 3 message templates (incident opened / approval requested / recovery update) 	Three clean runs
17:15–17:50 	Write the short writeup and the NVIDIA hardware answers (Hardware Expert supplies the facts) 	Ready to submit at 17:50
3. Checkpoints (everyone meets in the room for 5 minutes)
Time 	Must be true 	If not
15:15 	Agent answers in Telegram on local Qwen; stub tool server live; trigger method chosen 	Hardware switches to plain OpenClaw; Kunal uses the heartbeat fallback
16:00 	Agent calls real read endpoints; hog → degraded service → growing queue 	Cut: estimated value, customer ranking
16:45 	Full flow passes once, even if it's rough 	Cut: dashboard, message polish. Everyone works on the broken link
17:15 	Flow passes 3× from reset.sh; deny path works 	Record what works; narrate the rest honestly
4. The video (~2 minutes): shot list

    The problem (10 s): "A company runs an AI service for customers on its own GB10. At 2am it slows down…"
    Healthy start: terminal shows /health = healthy, queue flat; Telegram has no open incident.
    Local-first proof (10 s): docker ps (vLLM container) + nvidia-smi on the GB10.
    Fault: chaos/start_hog.sh; memory falls and the queue grows (split screen with watch).
    Detection: Telegram shows Incident opened, with no one typing.
    Investigation: the agent's tool calls with the evidence, plus impact numbers (e.g. 12 jobs across 3 customers delayed).
    Approval: the code arrives on the phone from the Approvals bot; the engineer types approve 4821.
    Fix + verification: only pitcrew-test-hog stops; memory and queue recover; Recovery update posts.
    Safety (stretch): a wrong code is refused.
    Close: "The investigation ran on the GB10 itself, with no cloud LLM. Pitcrew restores the service and tells you which customers were affected."

Record the healthy start → fixed sequence as one take, with timestamps visible on screen. That's the measured detection-to-recovery time for the pitch.
5. 18:00 submission checklist

    Repo pushed (commit history from today)
    Demo video uploaded
    Short writeup
    NVIDIA hardware questions answered
    18:00–19:00 slides with the video embedded → submitted by 19:00
    GB10 returned by 19:00 (Hardware Return check-in)

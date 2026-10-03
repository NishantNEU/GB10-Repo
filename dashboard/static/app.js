/* Pitcrew presenter console. All workflow mutations below are local demo state.
 * /api/live reads toolserver GET evidence; /api/fintech-example computes a packaged fixture.
 */

const $ = (id) => document.getElementById(id);
const STAGES = [
  { label: 'Monitor', detail: 'Service baseline' },
  { label: 'Detect', detail: 'Incident opens' },
  { label: 'Investigate', detail: 'Evidence trail' },
  { label: 'Decision', detail: 'Human approval' },
  { label: 'Jira ticket', detail: 'Track prevention' },
  { label: 'Patch & test', detail: 'Reproduce and verify' },
  { label: 'Stable', detail: 'Close the loop' },
];
const TRACE = [
  { title: 'Check service health', source: 'GET /health', detail: 'The sample AI service is degraded. Job throughput fell while the queue grew.', event: 'Service is processing slowly; customer jobs are stacking up.' },
  { title: 'Read host memory', source: 'GET /metrics', detail: 'GB10 memory used rose from 77 GB to 92 GB. This happened just before the slowdown.', event: 'Host memory climbed from 77 GB to 92 GB before the service degraded.' },
  { title: 'Find the new memory user', source: 'GET /processes/top', detail: 'pitcrew-test-hog is the #1 visible memory user. It is the labeled test workload.', event: 'The controlled test container is the largest visible memory user.' },
  { title: 'Read the service logs', source: 'GET /logs/service', detail: 'Memory pressure warnings line up with the time jobs began taking longer.', event: 'Service logs report memory pressure and slower processing.' },
  { title: 'Measure customer impact', source: 'GET /queue/status · /impact', detail: '18 sample jobs are delayed across 3 fictional customer accounts.', event: '18 delayed jobs are waiting across 3 fictional customers.' },
  { title: 'Check the safety boundary', source: 'Action allowlist', detail: 'Only pitcrew-test-hog is eligible for the guarded stop. The AI model is excluded.', event: 'The model is excluded; only the labeled test container can be stopped.' },
];
const TESTS = [
  { title: 'Reproduce original incident', detail: 'The existing 32 GB cap still lets host memory climb to 92 GB.', outcome: 'EXPECTED FAIL', kind: 'fail' },
  { title: 'Apply proposed cap in demo branch', detail: 'Limit the container to 8 GB and its payload to 7 GB.', outcome: 'PATCH APPLIED', kind: 'pass' },
  { title: 'Rerun memory pressure check', detail: 'Host stays under the degraded threshold.', outcome: 'PASS', kind: 'pass' },
  { title: 'Rerun service and queue check', detail: 'Service stays healthy and the sample queue drains.', outcome: 'PASS', kind: 'pass' },
];
const STORAGE_KEY = 'pitcrew-demo-v2';
let runToken = 0;
let toastTimer = null;
let live = null;
let sourceMode = 'scenario';

const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function initialState() {
  return {
    phase: 'monitor', incidentId: null, analysisCount: 0, testCount: 0,
    approved: false, mitigated: false, ticket: false, branch: false, stable: false,
    events: [
      { kind: 'system', title: 'Pitcrew started monitoring', detail: 'Sample AI service and job queue are healthy.', time: now() },
      { kind: 'system', title: 'Presenter scenario ready', detail: 'The guided investigation can be replayed without changing the GB10.', time: now() },
    ],
    messages: [],
  };
}

function loadState() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    if (saved && typeof saved.phase === 'string' && Array.isArray(saved.events) && Array.isArray(saved.messages)) {
      if (saved.phase === 'analyzing') { saved.phase = 'detected'; saved.analysisCount = 0; }
      if (saved.phase === 'approving') saved.phase = 'approval';
      if (saved.phase === 'running-tests') saved.phase = 'testing';
      if (saved.approved && !['approval', 'denied'].includes(saved.phase)) saved.mitigated = true;
      return saved;
    }
  } catch { /* A fresh walkthrough is safe if browser storage is unavailable. */ }
  return initialState();
}
let state = loadState();

function save() {
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* UI still works without storage. */ }
}
function addEvent(kind, title, detail) {
  state.events.push({ kind, title, detail, time: now() });
  state.events = state.events.slice(-65);
}
function addMessage(author, text) { state.messages.push({ author, text, time: now() }); }
function toast(message) {
  $('toast').textContent = message;
  $('toast').classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2700);
}

function stageIndex() {
  return ({ monitor: 0, detected: 1, analyzing: 2, verdict: 2, approval: 3,
    approving: 3, denied: 3, ticket: 4, patch: 5, testing: 5,
    'running-tests': 5, review: 5, stable: 6 })[state.phase] ?? 0;
}
function doneCount() {
  if (state.phase === 'stable') return 7;
  if (state.phase === 'review') return 6;
  return stageIndex();
}

function renderSide() {
  const active = stageIndex();
  $('sideSteps').innerHTML = STAGES.map((step, index) => {
    const complete = index < active || (state.phase === 'stable' && index === active);
    return `<li class="side-step ${complete ? 'complete' : ''} ${index === active && !complete ? 'active' : ''}" ${index === active ? 'aria-current="step"' : ''}>
    <span class="step-index">${complete ? '✓' : String(index + 1).padStart(2, '0')}</span>
    <span class="step-copy">${step.label}<small>${step.detail}</small></span></li>`;
  }).join('');
  $('workflowProgress').style.width = `${Math.round(doneCount() / 7 * 100)}%`;
  $('progressText').textContent = `${doneCount()} of 7 stages complete`;
  $('incidentId').textContent = state.incidentId || 'NO ACTIVE INCIDENT';
}

function scenarioMetrics() {
  const phase = state.phase;
  if (phase === 'monitor') return { memory: 77, status: 'Healthy', queue: 0, customers: 0, caption: 'Healthy baseline' };
  if (['detected', 'analyzing', 'verdict', 'approval', 'denied'].includes(phase)) return { memory: 92, status: 'Degraded', queue: 18, customers: 3, caption: 'Memory pressure detected' };
  if (phase === 'approving' && !state.mitigated) return { memory: 92, status: 'Degraded', queue: 18, customers: 3, caption: 'Awaiting guarded stop' };
  if (phase === 'review') return { memory: 77, status: 'Healthy', queue: 0, customers: 0, caption: 'Queue drained; awaiting sign-off' };
  if (['approving', 'ticket', 'patch', 'testing', 'running-tests'].includes(phase)) return { memory: 77, status: 'Healthy', queue: phase === 'approving' ? 18 : 6, customers: 3, caption: 'Memory returned to baseline' };
  return { memory: 77, status: 'Healthy', queue: 0, customers: 0, caption: 'Recovery verified' };
}

function renderMetrics() {
  const metric = scenarioMetrics();
  $('metricMemory').textContent = metric.memory;
  $('metricMemory').nextElementSibling.textContent = 'GB / 122 GB';
  $('metricService').textContent = metric.status;
  $('metricQueue').textContent = metric.queue;
  $('metricCustomers').textContent = metric.customers;
  $('memoryCaption').textContent = metric.caption;
  $('serviceCaption').textContent = metric.status === 'Degraded' ? 'Jobs processing slowly' : 'Jobs processing normally';
  $('queueCaption').textContent = metric.queue > 0 ? 'Customer work is waiting' : 'No work delayed';
  $('impactCaption').textContent = metric.customers > 0 ? 'Sample accounts affected' : 'No action required';
  const percent = Math.min(100, metric.memory / 122 * 100);
  $('memoryBar').style.width = `${percent}%`;
  $('memoryBar').classList.toggle('warning', percent >= 70);
  const degraded = String(metric.status).toLowerCase() === 'degraded';
  const stable = state.phase === 'stable';
  $('systemBadge').className = `status-badge ${degraded ? 'degraded' : stable ? 'stable' : 'healthy'}`;
  $('systemBadge').innerHTML = `<span></span>${degraded ? 'DEGRADED' : stable ? 'STABLE' : 'HEALTHY'}`;
  $('overviewTitle').textContent = degraded ? 'Memory pressure is slowing the service' : stable ? 'Incident resolved and verified' : state.phase === 'review' ? 'Service recovered; awaiting sign-off' : state.phase === 'monitor' ? 'Everything looks healthy' : 'Service recovered; queue draining';
}
function capitalize(value) { const text = String(value); return text.charAt(0).toUpperCase() + text.slice(1); }

function renderEvents() {
  $('eventHeading').textContent = sourceMode === 'live' ? 'Service logs' : 'Event stream';
  const items = sourceMode === 'live' ? (live?.data?.logs?.lines || []).map((line) => ({ kind: /warn|error/i.test(line) ? 'alert' : 'system', title: line, detail: 'GB10 service log', time: 'LIVE' })) : state.events;
  if (!items.length) {
    $('eventList').innerHTML = `<div class="telemetry-empty">${sourceMode === 'live' ? 'No live logs yet. Start the toolserver on the GB10, then this panel will update.' : 'No events yet.'}</div>`;
    return;
  }
  $('eventList').innerHTML = [...items].reverse().slice(0, 18).map((event) => `<div class="event-row"><span class="event-icon ${esc(event.kind)}">${event.kind === 'success' ? '✓' : event.kind === 'alert' ? '!' : event.kind === 'system' ? '·' : '⌕'}</span><div><time>${esc(event.time)}</time><strong>${esc(event.title)}</strong><p>${esc(event.detail)}</p></div></div>`).join('');
}

function renderTelemetry() {
  $('demoMode').classList.toggle('active', sourceMode === 'scenario');
  $('liveMode').classList.toggle('active', sourceMode === 'live');
  const indicator = $('liveIndicator');
  indicator.textContent = live?.connected ? `LIVE ${live.available_endpoints}/${live.total_endpoints}` : 'OFFLINE';
  indicator.className = `live-indicator ${live?.connected ? 'online' : 'offline'}`;
  if (sourceMode === 'scenario') {
    const metric = scenarioMetrics();
    $('telemetryContent').innerHTML = `<div class="telemetry-row"><span>Feed</span><strong>Illustrative scenario</strong></div>
      <div class="telemetry-row"><span>Host memory</span><strong class="${metric.memory > 85 ? 'warn' : ''}">${metric.memory} GB used</strong></div>
      <div class="telemetry-row"><span>Test workload</span><strong>${state.phase === 'monitor' ? 'Not running' : state.mitigated ? 'Stopped' : '#1 memory user'}</strong></div>
      <div class="telemetry-row"><span>Incident</span><strong>${esc(state.incidentId || 'None')}</strong></div>`;
    return;
  }
  if (!live?.connected) {
    $('telemetryContent').innerHTML = '<div class="telemetry-empty">The GB10 toolserver is not reachable from this dashboard. The scenario replay remains available.</div>';
    return;
  }
  const d = live.data;
  const top = d.processes?.processes?.[0];
  const sampled = new Date(live.sampled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  $('telemetryContent').innerHTML = `<div class="telemetry-row"><span>Sampled</span><strong>${esc(sampled)}</strong></div>
    <div class="telemetry-row"><span>Host memory</span><strong>${esc(d.metrics?.mem_used_gb ?? '—')} GB used</strong></div>
    <div class="telemetry-row"><span>Service</span><strong class="${d.health?.status === 'degraded' ? 'warn' : 'good'}">${esc(capitalize(d.health?.status ?? 'Unknown'))}</strong></div>
    <div class="telemetry-row"><span>Queue pending</span><strong>${esc(d.queue?.pending ?? '—')}</strong></div>
    <div class="telemetry-row"><span>Delayed jobs</span><strong>${esc(d.impact?.delayed_jobs ?? '—')}</strong></div>
    <div class="telemetry-row"><span>Longest queue wait</span><strong>${esc(d.impact?.longest_wait ?? '—')}</strong></div>
    <div class="telemetry-row"><span>Billable work waiting</span><strong>${d.impact?.estimated_value == null ? '—' : esc('$' + Number(d.impact.estimated_value).toFixed(2))}</strong></div>
    <div class="telemetry-row"><span>Top visible memory user</span><strong>${esc(top?.container || top?.name || '—')}</strong></div>
    <div class="telemetry-row"><span>Incident</span><strong>${esc(d.incident?.id || 'None')}</strong></div>`;
}

async function loadFintechExample() {
  try {
    const response = await fetch('/api/fintech-example', { cache: 'no-store' });
    if (!response.ok) throw new Error('Evidence unavailable');
    const { evidence: e } = await response.json();
    const amount = new Intl.NumberFormat(undefined, { style: 'currency', currency: e.currency }).format(e.affected_amount_cents / 100);
    $('fintechContent').innerHTML = `<p class="fintech-explainer">A separate payment-authentication incident, calculated from synthetic logs by the merged FinTech adapter.</p>
      <div class="fintech-metrics"><div><strong>${esc(e.failed_transactions)}</strong><span>failed payments</span></div><div><strong>${esc(e.affected_customers)}</strong><span>customers</span></div><div><strong>${esc(amount)}</strong><span>payment amount affected</span></div></div>
      <p class="fintech-caution">Affected payment amount is not lost revenue.</p>
      <details class="evidence-details"><summary>How these numbers were verified</summary><div class="evidence-detail-body"><p>${esc(e.received_error_events)} error events → ${esc(e.failed_transactions)} unique transactions. A retry of the same transaction is counted once.</p><p>Cause: <code>${esc(e.error_code)}</code>. Unexpected fields such as card data, tokens, and free-text messages are excluded from the evidence.</p><p>Source SHA-256 <code title="${esc(e.source_log_sha256)}">${esc(e.source_log_sha256.slice(0, 16))}…</code></p></div></details>`;
  } catch {
    $('fintechContent').innerHTML = '<p class="telemetry-empty">The packaged FinTech example could not be calculated.</p>';
  }
}

function renderSlack() {
  const messages = state.messages.length ? state.messages : [{ author: 'Pitcrew', text: 'Monitoring quietly. An approval request will appear here after the investigation.', time: now() }];
  $('slackMessages').innerHTML = messages.map((message) => `<div class="message"><span class="message-avatar ${message.author === 'On-call engineer' ? 'human' : ''}">${message.author === 'On-call engineer' ? 'N' : 'P'}</span><div class="message-content"><div class="message-line"><strong>${esc(message.author)}</strong><time>${esc(message.time)}</time></div><p>${esc(message.text)}</p></div></div>`).join('');
  $('slackActions').innerHTML = state.phase === 'approval' ? `<button type="button" class="button button-small button-primary" data-action="approve">Approve in Slack</button><button type="button" class="button button-small button-danger" data-action="deny">Deny</button>` : '';
}

function renderTicket() {
  $('ticketContent').innerHTML = !state.ticket ? `<div class="ticket-empty"><span class="ticket-empty-symbol">◇</span><span>No ticket yet. Pitcrew creates one after human approval.</span></div>` : `<div class="ticket-detail"><span class="ticket-id">PIT-104 · LINKED TO ${esc(state.incidentId)}</span><h4>Prevent test workload from starving the local AI service</h4><p>Owner: Platform team · Priority: High<br>Acceptance: capped memory, healthy service, queue drains.</p><span class="ticket-state ${state.stable ? 'done' : ''}">${state.stable ? 'DONE · VERIFIED' : state.branch ? 'IN TEST' : 'OPEN · REVIEW FIX'}</span></div>`;
}

function traceRows() {
  const count = state.phase === 'verdict' ? TRACE.length : state.analysisCount;
  return TRACE.map((step, index) => `<div class="trace-row ${index < count ? 'done' : index === count && state.phase === 'analyzing' ? 'active' : ''}" style="${index > count && state.phase === 'analyzing' ? 'opacity:.48' : ''}">
    <span class="trace-index">${index < count ? '✓' : index + 1}</span><div><h4>${step.title}</h4><p>${index < count ? step.detail : 'Waiting for this check…'}</p></div><span class="trace-source">${esc(step.source)}</span></div>`).join('');
}

function diffMarkup() {
  return `<div class="diff-window" aria-label="Illustrative proposed Git diff"><div class="diff-toolbar"><i class="dot"></i><i class="dot"></i><i class="dot"></i><strong>scripts/env.sh</strong><span>PROPOSED · NOT APPLIED</span></div><div class="diff-code">
    <span class="line context"><span class="sign"> </span>: "\${HOG_CONTAINER:=pitcrew-test-hog}"</span>
    <span class="line remove"><span class="sign">−</span>: "\${HOG_MEMORY_LIMIT:=32g}"</span>
    <span class="line remove"><span class="sign">−</span>: "\${HOG_MAX_GB:=30}"</span>
    <span class="line add"><span class="sign">+</span>: "\${HOG_MEMORY_LIMIT:=8g}"</span>
    <span class="line add"><span class="sign">+</span>: "\${HOG_MAX_GB:=7}"</span>
    <span class="line context"><span class="sign"> </span>: "\${HOG_MIN_FREE_GB:=16}"</span>
  </div></div>`;
}

function renderStage() {
  let body = '';
  let note = '';
  let buttons = [];
  switch (state.phase) {
    case 'monitor':
      body = `<p class="stage-eyebrow">01 / WATCH</p><h3 class="stage-title">A quiet baseline is your starting point.</h3><p class="stage-copy">A local AI service is processing customer jobs on the GB10. Pitcrew watches machine pressure, service health, and the queue. Start the replay to introduce the controlled fault.</p><div class="stage-hero"><span class="hero-orb">◉</span><div><strong>Ready to run the incident</strong><p>The presenter controls this synthetic memory spike. Nothing on the real GB10 is changed by the button.</p></div></div>`;
      note = 'Starts the scripted incident. No Docker command runs.';
      buttons = [['Simulate memory spike', 'trigger', 'button-primary']];
      break;
    case 'detected':
      body = `<p class="stage-eyebrow">02 / DETECT</p><h3 class="stage-title">The service slowed. An incident is open.</h3><p class="stage-copy">GB10 memory rose sharply, the sample service changed to degraded, and customer work began waiting. The detector groups these symptoms into one incident.</p><div class="stage-hero warning"><span class="hero-orb warning">!</span><div><strong>${esc(state.incidentId)} · Memory pressure</strong><p>18 delayed jobs · 3 fictional customers · service degraded after the controlled workload started.</p></div></div><div class="mini-callout"><strong>What happens next:</strong> the agent checks the machine, service logs, running programs, and customer impact before giving a verdict.</div>`;
      note = 'The investigation replay shows observable checks and evidence.';
      buttons = [['Bug identified · analyze', 'analyze', 'button-primary']];
      break;
    case 'analyzing':
    case 'verdict':
      body = `<p class="stage-eyebrow">03 / INVESTIGATE</p><h3 class="stage-title">${state.phase === 'verdict' ? 'The evidence points to one cause.' : 'Pitcrew is checking the evidence.'}</h3><p class="stage-copy">This is an evidence trail: the tools consulted, their observations, and the concise conclusion. It is a replayed explanation, not a live model transcript.</p><div class="trace">${traceRows()}</div><div class="trace-progress"><span style="width:${Math.round(state.analysisCount / TRACE.length * 100)}%"></span></div>${state.phase === 'verdict' ? `<div class="verdict-box" style="margin-top:16px"><p><strong>Verdict:</strong> the labeled test container is the likely cause. It became the top memory user as host memory rose, and the service logs show pressure at the same time. Stop only that container after human approval; then verify recovery.</p></div><div class="impact-panel"><div class="impact-stat"><strong>18</strong><small>delayed sample jobs</small></div><div class="impact-stat"><strong>3</strong><small>fictional customers</small></div><div class="impact-stat"><strong>~$45</strong><small>billable work waiting</small></div></div><p class="impact-label">Illustrative estimate of work waiting, not lost revenue.</p><div class="evidence-pills"><span>Model excluded from stop allowlist</span><span>Local GB10 investigation</span><span>Human approval required</span></div>` : ''}`;
      note = state.phase === 'verdict' ? 'No action is taken until the simulated human approval.' : `${state.analysisCount} of ${TRACE.length} evidence checks shown`;
      buttons = state.phase === 'verdict' ? [['Send approval to Slack', 'send-approval', 'button-primary']] : [['Show all checks', 'finish-analysis', 'button-outline']];
      break;
    case 'approval':
    case 'approving':
      body = `<p class="stage-eyebrow">04 / HUMAN GATE</p><h3 class="stage-title">${state.phase === 'approving' ? 'Approval received. Applying the guarded action.' : 'A person makes the decision.'}</h3><p class="stage-copy">Pitcrew posts the verdict and exact target in a simulated Slack thread. The proposed action is limited to the labeled test container. The real backend separately proved this guard on the GB10.</p><div class="approval-preview"><div class="preview-top"><strong>#incident-response</strong><span>${esc(state.incidentId)}</span></div><h4>Approval requested · stop test workload</h4><p>Target: <code>pitcrew-test-hog</code> only. Reason: top visible memory user; service degraded with 18 delayed jobs. The AI model is explicitly excluded.</p></div><div class="mini-callout"><strong>Safety rule:</strong> the real toolserver requires a current incident, a valid one-time code, and the labeled test container before a stop can occur. This screen simulates the decision.</div>`;
      note = state.phase === 'approving' ? 'Recording approval and recovery in the replay…' : 'Approve or deny from the simulated Slack panel.';
      buttons = state.phase === 'approving' ? [] : [['Approve in Slack', 'approve', 'button-primary'], ['Deny', 'deny', 'button-danger']];
      break;
    case 'denied':
      body = `<p class="stage-eyebrow">04 / HUMAN GATE</p><h3 class="stage-title">Approval was denied.</h3><p class="stage-copy">Pitcrew does not stop the test workload. The incident stays open for a person to investigate further. Reset the walkthrough to demonstrate the approval path.</p><div class="stage-hero warning"><span class="hero-orb warning">×</span><div><strong>No action performed</strong><p>No Jira ticket or branch was created from the denied proposal.</p></div></div>`;
      note = 'Denied actions are not retried automatically.';
      buttons = [['Reset walkthrough', 'reset', 'button-outline']];
      break;
    case 'ticket':
      body = `<p class="stage-eyebrow">05 / TRACK THE FIX</p><h3 class="stage-title">Mitigated now. Prevent recurrence next.</h3><p class="stage-copy">The simulated approval allowed only the guarded stop. Memory returned to baseline and the service recovered. A simulated Jira issue now tracks the durable prevention work.</p><div class="ticket-preview"><span class="ticket-top">PIT-104 · HIGH PRIORITY · ${esc(state.incidentId)}</span><h4>Prevent test workload from starving the local AI service</h4><p>Proposed owner: Platform team. Acceptance: cap the workload, reproduce the old failure, then show that service health and the customer queue remain normal.</p><div class="ticket-meta"><span>OPEN</span><span>3 sample customers</span><span>18 jobs initially delayed</span></div></div><div class="mini-callout"><strong>Customer value:</strong> Pitcrew shows who is waiting and the estimated billable work delayed. These are sample records, not claimed revenue loss.</div>`;
      note = 'The Jira issue exists only inside this presentation.';
      buttons = [['Review proposed fix', 'show-patch', 'button-primary']];
      break;
    case 'patch':
      body = `<p class="stage-eyebrow">06 / SUGGEST A CHANGE</p><h3 class="stage-title">A small, reviewable code suggestion.</h3><p class="stage-copy">Pitcrew proposes a lower cap for the controlled test workload. The Git-style diff is illustrative and has not modified the real repository. The team can review the exact lines before any real change.</p>${diffMarkup()}<div class="branch-card"><span class="branch-icon">⑂</span><div><strong>fix/limit-test-workload</strong><small>Simulated branch from the demo's main revision</small></div></div>`;
      note = 'Create a simulated branch to walk through validation.';
      buttons = [['Create demo branch', 'create-branch', 'button-primary']];
      break;
    case 'testing':
    case 'running-tests':
    case 'review':
      body = `<p class="stage-eyebrow">06 / VALIDATE</p><h3 class="stage-title">${state.phase === 'review' ? 'The proposed fix passes the replayed checks.' : 'Reproduce. Patch. Test again.'}</h3><p class="stage-copy">The test walkthrough makes the cause-and-effect visible: the original scenario degrades the service, then the capped workload keeps the host and queue healthy.</p><div class="test-stack">${TESTS.map((test, index) => `<div class="test-row ${index < state.testCount ? test.kind : index === state.testCount && state.phase === 'running-tests' ? 'running' : ''}"><span class="test-icon">${index < state.testCount ? test.kind === 'fail' ? '!' : '✓' : index === state.testCount && state.phase === 'running-tests' ? '↻' : index + 1}</span><span>${test.title}</span><strong>${index < state.testCount ? test.outcome : 'WAITING'}</strong></div>`).join('')}</div><div class="test-summary"><div><strong>${state.testCount === 4 ? '4 / 4' : `${state.testCount} / 4`}</strong><small>Replay steps complete</small></div><div><strong>${state.testCount === 4 ? 'Healthy' : 'Pending'}</strong><small>Service after patch</small></div><div><strong>${state.testCount === 4 ? '0' : '—'}</strong><small>Jobs waiting after recovery</small></div></div><div class="mini-callout"><strong>Note:</strong> the first “expected fail” is the reproduced original bug. It is evidence that the test can detect the problem.</div>`;
      note = state.phase === 'review' ? 'Human sign-off closes the simulated Jira ticket.' : state.phase === 'running-tests' ? 'Running the scripted validation…' : 'The walkthrough does not run real Git or test commands.';
      buttons = state.phase === 'review' ? [['Mark stable & close ticket', 'mark-stable', 'button-primary']] : state.phase === 'testing' ? [['Run replayed tests', 'run-tests', 'button-primary']] : [];
      break;
    case 'stable':
      body = `<p class="stage-eyebrow">07 / CLOSE THE LOOP</p><h3 class="stage-title">The incident is stable and explained.</h3><p class="stage-copy">The presentation shows a complete decision record: detection, evidence, human approval, guarded mitigation, a tracked prevention proposal, and replayed validation.</p><div class="stable-banner"><h3>✓ Stable · ${esc(state.incidentId)} resolved</h3><p>Service healthy. Memory back to baseline. Sample queue drained. Jira PIT-104 marked done after presenter sign-off.</p></div><div class="stable-grid"><div><small>Service</small><strong>Healthy</strong></div><div><small>Jobs waiting</small><strong>0</strong></div><div><small>Ticket</small><strong>PIT-104 · Done</strong></div></div><div class="mini-callout"><strong>What was real:</strong> the backend, guardrails, and Docker stop were tested on the GB10. This UI replay demonstrates the full product story and clearly labels its simulated integrations.</div>`;
      note = 'Ready for another presenter run.';
      buttons = [['Replay incident', 'reset', 'button-primary']];
      break;
  }
  $('stageBody').innerHTML = body;
  $('stageActions').innerHTML = `<span class="action-note">${note}</span><span class="action-buttons">${buttons.map(([label, action, type]) => `<button type="button" class="button ${type}" data-action="${action}">${label}${type === 'button-primary' ? ' →' : ''}</button>`).join('')}</span>`;
}

function render() { renderSide(); renderMetrics(); renderEvents(); renderTelemetry(); renderSlack(); renderTicket(); renderStage(); save(); }

function reset() { runToken += 1; state = initialState(); sourceMode = 'scenario'; render(); toast('Walkthrough reset'); }
function trigger() {
  if (state.phase !== 'monitor') return;
  state.phase = 'detected'; state.incidentId = 'INC-1042';
  addEvent('alert', 'Memory pressure detected', 'Host memory rose from 77 GB to 92 GB; service degraded after 45 seconds.');
  addEvent('alert', 'Incident INC-1042 opened', '18 delayed sample jobs and 3 fictional customers are affected.');
  render(); toast('Synthetic incident opened');
}
async function analyze() {
  if (state.phase !== 'detected') return;
  const token = ++runToken;
  state.phase = 'analyzing'; state.analysisCount = 0;
  addEvent('tool', 'Investigation started', 'NemoClaw-style evidence checks are replaying in the presenter UI.');
  render();
  for (let index = 0; index < TRACE.length; index++) {
    await pause(860);
    if (token !== runToken) return;
    state.analysisCount = index + 1;
    addEvent('tool', TRACE[index].title, TRACE[index].event);
    render();
  }
  await pause(500);
  if (token !== runToken) return;
  finishAnalysis();
}
function finishAnalysis() {
  if (!['analyzing', 'detected'].includes(state.phase)) return;
  runToken += 1;
  state.phase = 'verdict'; state.analysisCount = TRACE.length;
  addEvent('success', 'Final verdict ready', 'The labeled test container is the likely cause; human approval is required before mitigation.');
  render(); toast('Verdict ready');
}
function sendApproval() {
  if (state.phase !== 'verdict') return;
  state.phase = 'approval';
  addMessage('Pitcrew', `Approval requested for ${state.incidentId}: stop only pitcrew-test-hog. The service is degraded, 18 sample jobs are delayed, and the AI model is excluded. Approve or deny.`);
  addEvent('alert', 'Approval request posted', 'Simulated Slack request contains the exact action, target, reason, and incident.');
  render(); toast('Simulated Slack request sent');
}
async function approve() {
  if (state.phase !== 'approval') return;
  const token = ++runToken;
  state.phase = 'approving'; state.approved = true;
  addMessage('On-call engineer', 'Approved for pitcrew-test-hog only.');
  addEvent('success', 'Human approval recorded', 'The simulated decision authorizes only the labeled test workload.');
  render();
  await pause(850); if (token !== runToken) return;
  state.mitigated = true;
  addEvent('tool', 'Guarded mitigation replayed', 'The approved stop targets only pitcrew-test-hog; the local AI model remains running.');
  addMessage('Pitcrew', 'The guarded stop completed in the replay. Memory returned toward baseline; checking service recovery.');
  render();
  await pause(950); if (token !== runToken) return;
  state.phase = 'ticket'; state.ticket = true;
  addEvent('success', 'Service recovered', 'Host available memory returned to about 44 GB and the service became healthy.');
  addEvent('tool', 'Jira ticket PIT-104 created', 'Simulated ticket tracks the preventive change and validation.');
  addMessage('Pitcrew', 'Service healthy. Jira PIT-104 created to prevent the test workload from causing this again.');
  render(); toast('Recovery shown · Jira ticket created');
}
function deny() {
  if (state.phase !== 'approval') return;
  state.phase = 'denied';
  addMessage('On-call engineer', 'Denied. Continue investigation; do not stop the workload.');
  addEvent('alert', 'Action denied', 'No container was stopped and no ticket was created.');
  render(); toast('Denied — no action taken');
}
function showPatch() { if (state.phase === 'ticket') { state.phase = 'patch'; render(); } }
function createBranch() {
  if (state.phase !== 'patch') return;
  state.phase = 'testing'; state.branch = true;
  addEvent('tool', 'Demo branch created', 'Simulated fix/limit-test-workload branch contains the proposed memory cap.');
  render(); toast('Demo branch created');
}
async function runTests() {
  if (state.phase !== 'testing') return;
  const token = ++runToken;
  state.phase = 'running-tests'; state.testCount = 0; render();
  for (let index = 0; index < TESTS.length; index++) {
    await pause(800);
    if (token !== runToken) return;
    state.testCount = index + 1;
    addEvent(index === 0 ? 'alert' : 'success', TESTS[index].title, TESTS[index].detail);
    render();
  }
  await pause(400); if (token !== runToken) return;
  state.phase = 'review';
  addEvent('success', 'Validation complete', 'Original fault reproduced; proposed cap keeps service healthy in the replay.');
  render(); toast('Scripted tests complete');
}
function markStable() {
  if (state.phase !== 'review') return;
  state.phase = 'stable'; state.stable = true;
  addEvent('success', 'Incident closed', 'Service healthy; queue drained; simulated Jira PIT-104 marked done.');
  addMessage('Pitcrew', `${state.incidentId} stable. Service healthy, sample queue drained, and Jira PIT-104 marked done after sign-off.`);
  render(); toast('Incident marked stable');
}

const actions = { reset, trigger, analyze, 'finish-analysis': finishAnalysis, 'send-approval': sendApproval,
  approve, deny, 'show-patch': showPatch, 'create-branch': createBranch, 'run-tests': runTests, 'mark-stable': markStable };
document.addEventListener('click', (event) => {
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (action && actions[action]) actions[action]();
});
$('resetBtn').addEventListener('click', reset);
$('resetTop').addEventListener('click', reset);
$('demoMode').addEventListener('click', () => { sourceMode = 'scenario'; render(); });
$('liveMode').addEventListener('click', () => { sourceMode = 'live'; render(); pollLive(); });

async function pollLive() {
  try {
    const response = await fetch('/api/live', { cache: 'no-store' });
    if (!response.ok) throw new Error('offline');
    live = await response.json();
  } catch {
    live = { connected: false, data: {} };
  }
  renderMetrics(); renderEvents(); renderTelemetry();
}
render();
pollLive();
loadFintechExample();
setInterval(() => { if (sourceMode === 'live') pollLive(); }, 5000);

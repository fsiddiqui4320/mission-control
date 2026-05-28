/* Mission Control v2 — main app logic
   Zero demo data. All data from live API. Every tab handles loading/error/empty states. */

let API_BASE = '';

// ── API client ─────────────────────────────────────────────────

const API = {
  async get(endpoint) {
    if (!API_BASE) return null;
    try {
      const res = await fetch(API_BASE + endpoint, { signal: AbortSignal.timeout(8000) });
      if (res.ok) return await res.json();
      if (res.status >= 400) console.warn(`API ${endpoint}: ${res.status}`);
    } catch (e) {
      console.warn(`API ${endpoint}: ${e.message}`);
    }
    return null;
  },

  async post(endpoint, body) {
    if (!API_BASE) return null;
    try {
      const res = await fetch(API_BASE + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(10000),
      });
      return await res.json();
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }
};

// ── Tunnel discovery ──────────────────────────────────────────

const DISCOVERY_URL = 'https://api.github.com/repos/fsiddiqui4320/mission-control/contents/tunnel-url.txt';

async function discoverTunnelURL() {
  try {
    const res = await fetch(DISCOVERY_URL, { cache: 'no-cache', signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      const data = await res.json();
      if (data.content) {
        const url = atob(data.content.replace(/\s/g, '')).trim();
        if (url.startsWith('https://') && url.includes('trycloudflare.com')) return url;
      }
    }
  } catch (e) {}
  return null;
}

// ── Auto-connect ──────────────────────────────────────────────

const apiUrlInput = document.getElementById('api-url');
const apiLabel = document.getElementById('api-label');
const apiIndicator = document.querySelector('.api-indicator');
const statusDot = document.getElementById('status-dot');
const mobileStatus = document.getElementById('mobile-status');
const connectionStatus = document.getElementById('connection-status');

function setConnected(label) {
  apiLabel.textContent = label || 'Connected';
  apiIndicator.className = 'api-indicator connected';
  statusDot.className = 'status-dot connected';
  mobileStatus.className = 'connected';
  connectionStatus.textContent = '● Connected';
}

function setDisconnected() {
  apiLabel.textContent = 'Disconnected';
  apiIndicator.className = 'api-indicator disconnected';
  statusDot.className = 'status-dot disconnected';
  mobileStatus.className = 'disconnected';
  connectionStatus.textContent = '● Disconnected';
}

async function autoConnect() {
  // 1. Try GitHub-discovered tunnel URL
  const tunnelURL = await discoverTunnelURL();
  if (tunnelURL) {
    API_BASE = tunnelURL;
    apiUrlInput.value = tunnelURL;
    const status = await API.get('/api/status');
    if (status && status.ok) {
      setConnected('Live (tunnel)');
      loadCurrentTab();
      return;
    }
    API_BASE = '';
  }

  // 2. Try localhost
  const localURL = 'http://localhost:5555';
  API_BASE = localURL;
  apiUrlInput.value = localURL;
  const status = await API.get('/api/status');
  if (status && status.ok) {
    setConnected('Live (local)');
    loadCurrentTab();
    return;
  }

  // 3. Fail — show disconnected state
  API_BASE = '';
  setDisconnected();
  renderEmptyState('quick-stats', 'No connection');
  renderEmptyState('pulse-sessions', 'Connect to see live data');
}

document.getElementById('api-connect-btn').addEventListener('click', async () => {
  const url = apiUrlInput.value.replace(/\/$/, '');
  API_BASE = url;
  const status = await API.get('/api/status');
  if (status && status.ok) {
    setConnected('Connected');
    loadCurrentTab();
  } else {
    API_BASE = '';
    setDisconnected();
  }
});

apiUrlInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('api-connect-btn').click();
});

// ── Tab navigation ────────────────────────────────────────────

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    item.classList.add('active');
    document.getElementById('tab-' + item.dataset.tab).classList.add('active');
    loadTab(item.dataset.tab);
    if (window.innerWidth < 768) closeSidebar();
  });
});

const tabLoaders = {
  pulse:       loadPulse,
  projects:    loadProjects,
  cron:        loadCron,
  health:      loadHealth,
  memory:      loadMemory,
  bottlenecks: loadBottlenecks,
};

function loadCurrentTab() {
  const active = document.querySelector('.tab-content.active');
  if (!active) return;
  const name = active.id.replace('tab-', '');
  if (tabLoaders[name]) tabLoaders[name]();
}

function loadTab(name) {
  if (tabLoaders[name]) tabLoaders[name]();
}

// ── Mobile sidebar ────────────────────────────────────────────

const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('sidebar-overlay');
const hamburger = document.getElementById('hamburger');

function openSidebar() {
  sidebar.classList.add('open');
  overlay.classList.add('visible');
  hamburger.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeSidebar() {
  sidebar.classList.remove('open');
  overlay.classList.remove('visible');
  hamburger.classList.remove('open');
  document.body.style.overflow = '';
}
hamburger.addEventListener('click', () => sidebar.classList.contains('open') ? closeSidebar() : openSidebar());
overlay.addEventListener('click', closeSidebar);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSidebar(); });

// ── UI helpers ────────────────────────────────────────────────

function renderEmptyState(id, msg) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<div class="empty-state">${msg || 'No data'}</div>`;
}

function renderError(id, msg) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<div class="error-state">⚠️ ${msg || 'Failed to load'}</div>`;
}

function renderLoading(id) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = '<div class="loading">Loading…</div>';
}

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
  return Math.floor(diff / 86400000) + 'd ago';
}

function fmtBytes(b) {
  if (!b) return '0 B';
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(1) + ' MB';
}

function statusDot2(status) {
  const map = { ok: '🟢', active: '🟢', error: '🔴', error_recent: '🔴', failed: '🔴',
                overdue: '🟡', warning: '🟡', never_run: '⚪', idle: '⚪',
                disabled: '⚫', aborted: '🔴' };
  return map[status] || '⚪';
}

// ── Tab: Pulse ────────────────────────────────────────────────

async function loadPulse() {
  renderLoading('quick-stats');
  renderLoading('pulse-sessions');
  renderLoading('pulse-activity');

  const resp = await API.get('/api/pulse');
  if (!resp || !resp.ok) {
    renderError('quick-stats', 'API unreachable');
    renderEmptyState('pulse-sessions', '');
    renderEmptyState('pulse-activity', '');
    return;
  }

  const data = resp.data;
  const qs = data.quick_stats || {};
  const sessions = data.active_sessions || [];
  const activity = data.recent_activity || [];
  const agent = data.agent_status || {};

  // Quick stats
  document.getElementById('quick-stats').innerHTML = `
    <div class="stat-card"><div class="stat-num">${qs.active_session_count}</div><div class="stat-label">Sessions</div></div>
    <div class="stat-card"><div class="stat-num">${qs.recent_file_changes}</div><div class="stat-label">File Changes (24h)</div></div>
    <div class="stat-card"><div class="stat-num">${(qs.total_tokens_used / 1000).toFixed(0)}k</div><div class="stat-label">Tokens</div></div>
    <div class="stat-card"><div class="stat-num">${agent.status || 'idle'}</div><div class="stat-label">Agent</div></div>
  `;
  document.getElementById('pulse-age').textContent = fmtTime(resp.meta?.cached_at);

  // Sessions
  if (!sessions.length) {
    renderEmptyState('pulse-sessions', 'No active sessions');
  } else {
    let html = '';
    const shown = sessions.slice(0, 15);
    for (const s of shown) {
      const surf = s.surface || 'unknown';
      const modelShort = (s.model || '?').replace('deepseek-v4-pro', 'DSv4').replace('claude-sonnet-4', 'Sonnet4').replace('gpt-4o', 'GPT4o');
      html += `<div class="session-row">
        <span class="session-kind">${s.kind || '?'}</span>
        <span class="session-surface ${surf}">${surf}</span>
        <span class="session-model">${modelShort}</span>
        <span class="session-age">${s.age || '?'}</span>
        <span class="session-tokens">${(s.tokens_used / 1000).toFixed(0)}k</span>
        <span class="session-status">${statusDot2(s.status)}</span>
      </div>`;
    }
    if (sessions.length > 15) html += `<div class="more-row">+${sessions.length - 15} more sessions</div>`;
    document.getElementById('pulse-sessions').innerHTML = html;
  }

  // Activity feed
  if (!activity.length) {
    renderEmptyState('pulse-activity', 'No recent file activity');
  } else {
    let html = '';
    for (const f of activity.slice(0, 8)) {
      html += `<div class="activity-row">
        <span class="activity-icon">📄</span>
        <span class="activity-path">${f.path || f.name}</span>
        <span class="activity-time">${fmtTime(f.modified)}</span>
      </div>`;
    }
    document.getElementById('pulse-activity').innerHTML = html;
  }
}

// ── Tab: Projects ─────────────────────────────────────────────

let projectsData = [];
let projectSort = 'recent';

async function loadProjects() {
  renderLoading('projects-grid');
  const resp = await API.get('/api/projects');
  if (!resp || !resp.ok) { renderError('projects-grid', 'Failed to load projects'); return; }
  const list = resp.data || [];
  document.getElementById('projects-age').textContent = fmtTime(resp.meta?.cached_at);
  renderProjectList(list);
}

function renderProjectList(list) {
  if (!list.length) { renderEmptyState('projects-grid', 'No projects found'); return; }
  projectsData = list;
  sortProjects();
}

function sortProjects() {
  const sorted = [...projectsData];
  if (projectSort === 'recent') sorted.sort((a, b) => (b.modified || '').localeCompare(a.modified || ''));
  else if (projectSort === 'name') sorted.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  else if (projectSort === 'tasks') sorted.sort((a, b) => (b.task_count || 0) - (a.task_count || 0));

  let html = '';
  for (const p of sorted) {
    const days = p.age_days || 0;
    const staleClass = days > 14 ? 'stale' : days > 7 ? 'warn' : 'fresh';
    html += `<div class="project-card ${staleClass}">
      <div class="project-name">${p.name || '?'}</div>
      <div class="project-meta">
        <span>📄 ${p.file_count || 0} files</span>
        <span>✅ ${p.task_count || 0} tasks</span>
        <span>${p.has_spec ? '📋 Spec' : ''}</span>
      </div>
      <div class="project-age">${fmtTime(p.modified)}</div>
    </div>`;
  }
  document.getElementById('projects-grid').innerHTML = html;
}

document.querySelectorAll('.sort-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    projectSort = btn.dataset.sort;
    sortProjects();
  });
});

// ── Tab: Cron ─────────────────────────────────────────────────

async function loadCron() {
  renderLoading('cron-summary');
  renderLoading('cron-list');
  const resp = await API.get('/api/cron');
  if (!resp || !resp.ok) { renderError('cron-list', 'Failed to load cron jobs'); return; }
  const data = resp.data || {};
  const jobs = data.jobs || [];
  const summary = data.summary || {};
  document.getElementById('cron-age').textContent = fmtTime(resp.meta?.cached_at);

  // Summary
  document.getElementById('cron-summary').innerHTML = `
    <span class="badge ok">${summary.ok || 0} OK</span>
    <span class="badge error">${summary.error || 0} Failed</span>
    <span class="badge">${summary.enabled || 0} Enabled</span>
  `;

  // Job list
  if (!jobs.length) { renderEmptyState('cron-list', 'No cron jobs configured'); return; }
  let html = '';
  for (const j of jobs) {
    html += `<div class="cron-row ${j.last_status || ''}" id="cron-${j.id}">
      <div class="cron-info">
        <span class="cron-dot">${statusDot2(j.last_status)}</span>
        <div>
          <div class="cron-name">${j.name || j.id?.slice(0, 8)}</div>
          <div class="cron-schedule">${j.schedule || '?'} ${j.next_run ? '· Next: ' + fmtTime(j.next_run) : ''}</div>
          ${j.last_error ? `<div class="cron-error-msg">${j.last_error.slice(0, 120)}</div>` : ''}
        </div>
      </div>
      <div class="cron-actions">
        <span class="cron-last">Last: ${j.last_run ? fmtTime(j.last_run) : 'never'}</span>
        <button class="cron-trigger-btn" onclick="triggerCron('${j.id}', '${j.name || ''}')" ${!j.enabled ? 'disabled' : ''}>▶ Run</button>
      </div>
    </div>`;
  }
  document.getElementById('cron-list').innerHTML = html;
}

async function triggerCron(id, name) {
  if (!confirm(`Run "${name || id.slice(0, 8)}" now?`)) return;
  const btn = document.querySelector(`#cron-${CSS.escape(id)} .cron-trigger-btn`);
  if (btn) { btn.textContent = '…'; btn.disabled = true; }
  const resp = await API.post('/api/actions/trigger', { action: 'cron:run:' + id });
  if (btn) { btn.textContent = resp?.ok ? '✓' : '✗'; btn.disabled = false; }
  if (resp?.ok) loadCron();
}

// ── Tab: Health ───────────────────────────────────────────────

async function loadHealth() {
  ['health-gateway', 'health-channels', 'health-tunnel', 'health-workspace'].forEach(id => {
    const card = document.getElementById(id);
    if (card) card.querySelector('.health-body').innerHTML = '<div class="loading">…</div>';
  });
  const resp = await API.get('/api/health');
  if (!resp || !resp.ok) {
    ['health-gateway', 'health-channels', 'health-tunnel', 'health-workspace'].forEach(id => {
      const card = document.getElementById(id);
      if (card) card.querySelector('.health-body').innerHTML = '<div class="error-state">Unavailable</div>';
    });
    return;
  }
  const data = resp.data || {};
  document.getElementById('health-age').textContent = fmtTime(resp.meta?.cached_at);

  // Gateway
  const gw = data.gateway || {};
  document.querySelector('#health-gateway .health-body').innerHTML = `
    <div class="health-stat ${gw.connected ? 'ok' : 'error'}">${gw.connected ? '🟢 Connected' : '🔴 Disconnected'}</div>
    ${gw.version ? `<div class="health-stat">Version: ${gw.version}</div>` : ''}
    ${gw.error ? `<div class="health-stat error">${gw.error.slice(0, 80)}</div>` : ''}
  `;

  // Channels
  const channels = data.channels || {};
  let chHTML = '';
  for (const [name, ch] of Object.entries(channels)) {
    const ok = ch.connected;
    chHTML += `<div class="health-stat ${ok === true ? 'ok' : ok === false ? 'error' : ''}">${ok === true ? '🟢' : ok === false ? '🔴' : '⚪'} ${name}${ch.enabled !== undefined ? (ch.enabled ? '' : ' (disabled)') : ''}</div>`;
  }
  if (!chHTML) chHTML = '<div class="health-stat">No channel data</div>';
  document.querySelector('#health-channels .health-body').innerHTML = chHTML;

  // Tunnel
  const tunnel = data.tunnel || {};
  document.querySelector('#health-tunnel .health-body').innerHTML = `
    <div class="health-stat ${tunnel.active ? 'ok' : 'error'}">${tunnel.active ? '🟢 Active' : '🔴 Inactive'}</div>
    ${tunnel.url ? `<div class="health-stat mono">${tunnel.url.slice(0, 45)}…</div>` : ''}
    <div class="health-stat">Process: ${tunnel.process_running === true ? '✅ Running' : tunnel.process_running === false ? '❌ Stopped' : '?'}</div>
  `;

  // Workspace
  const ws = data.workspace || {};
  document.querySelector('#health-workspace .health-body').innerHTML = `
    <div class="health-stat">Size: ${ws.workspace_size_mb} MB</div>
    <div class="health-stat">Sessions: ${ws.session_count}</div>
    <div class="health-stat">Memory files: ${ws.memory_files}</div>
  `;
}

// ── Tab: Memory ───────────────────────────────────────────────

let memoryData = null;

async function loadMemory() {
  renderLoading('memory-daily');
  renderLoading('memory-areas');
  const resp = await API.get('/api/memories');
  if (!resp || !resp.ok) { renderError('memory-daily', 'Failed to load'); return; }
  const data = resp.data || {};
  memoryData = data;

  // Daily notes
  const daily = data.daily || [];
  let dHTML = '';
  for (const m of daily.slice(0, 12)) {
    dHTML += `<div class="memory-row">
      <span class="memory-name">📅 ${m.relative || m.name}</span>
      <span class="memory-meta">${fmtBytes(m.size)} · ${fmtTime(m.modified)}</span>
    </div>`;
  }
  if (!dHTML) dHTML = '<div class="empty-state">No daily notes</div>';
  document.getElementById('memory-daily').innerHTML = dHTML;

  // Areas
  const areas = data.areas || [];
  let aHTML = '';
  for (const m of areas.slice(0, 12)) {
    aHTML += `<div class="memory-row">
      <span class="memory-name">📂 ${m.relative || m.name}</span>
      <span class="memory-meta">${fmtBytes(m.size)} · ${fmtTime(m.modified)}</span>
    </div>`;
  }
  if (!aHTML) aHTML = '<div class="empty-state">No area files</div>';
  document.getElementById('memory-areas').innerHTML = aHTML;

  // Search
  document.getElementById('memory-search').oninput = function () {
    const q = this.value.toLowerCase();
    if (!memoryData) return;
    const all = [...(memoryData.daily || []), ...(memoryData.areas || []), ...(memoryData.resources || []), ...(memoryData.other || [])];
    const filtered = q ? all.filter(m => (m.relative || m.name || '').toLowerCase().includes(q)) : [];
    if (q) {
      let html = filtered.length ? '' : '<div class="empty-state">No matches</div>';
      for (const m of filtered.slice(0, 20)) {
        html += `<div class="memory-row"><span class="memory-name">📄 ${m.relative || m.name}</span><span class="memory-meta">${fmtBytes(m.size)}</span></div>`;
      }
      document.getElementById('memory-daily').innerHTML = html;
      document.getElementById('memory-areas').innerHTML = '';
    } else {
      loadMemory();
    }
  };
}

// ── Tab: Bottlenecks ──────────────────────────────────────────

async function loadBottlenecks() {
  renderLoading('bottlenecks-list');
  const resp = await API.get('/api/bottlenecks');
  if (!resp || !resp.ok) { renderError('bottlenecks-list', 'Failed to load'); return; }
  const data = resp.data || {};
  document.getElementById('bottlenecks-age').textContent = fmtTime(resp.meta?.cached_at);

  const total = data.total_issues || 0;
  document.getElementById('bottlenecks-summary').innerHTML = total === 0
    ? '<div class="empty-state">✅ No issues detected</div>'
    : `<div class="issues-count">${total} issue${total !== 1 ? 's' : ''} need attention</div>`;

  let html = '';

  // Blockers
  const blockers = data.blockers || [];
  if (blockers.length) html += '<div class="section"><h3>🚧 Blockers</h3>';
  for (const b of blockers) {
    html += `<div class="issue-card ${b.severity}">
      <div class="issue-name">${statusDot2(b.severity)} ${b.name}</div>
      <div class="issue-desc">${b.description || ''}</div>
      ${b.deadline_hint ? `<div class="issue-meta">📅 ${b.deadline_hint}</div>` : ''}
    </div>`;
  }
  if (blockers.length) html += '</div>';

  // Deadlines
  const deadlines = data.deadlines || [];
  if (deadlines.length) html += '<div class="section"><h3>📅 Deadlines</h3>';
  for (const d of deadlines) {
    html += `<div class="issue-card ${d.severity}">
      <div class="issue-name">${statusDot2(d.severity)} ${d.name}</div>
      <div class="issue-desc">${d.description || ''}</div>
      ${d.deadline ? `<div class="issue-meta">⏰ ${d.deadline}</div>` : ''}
    </div>`;
  }
  if (deadlines.length) html += '</div>';

  // Stale projects
  const stale = data.stale_projects || [];
  if (stale.length) html += '<div class="section"><h3>💤 Stale Projects (14+ days)</h3>';
  for (const p of stale) {
    html += `<div class="issue-card info">
      <div class="issue-name">📁 ${p.name}</div>
      <div class="issue-meta">${p.age_days} days since last activity</div>
    </div>`;
  }
  if (stale.length) html += '</div>';

  // Failed cron
  const failed = data.failed_cron || [];
  if (failed.length) html += '<div class="section"><h3>❌ Failed Cron Jobs</h3>';
  for (const f of failed) {
    html += `<div class="issue-card ${f.severity}">
      <div class="issue-name">${statusDot2(f.severity)} ${f.job_id?.slice(0, 12)}…</div>
      <div class="issue-desc">${f.error || 'Unknown error'}</div>
      <div class="issue-meta">${f.consecutive_errors} consecutive failures · Last: ${fmtTime(f.last_run)}</div>
    </div>`;
  }
  if (failed.length) html += '</div>';

  if (!html) html = '<div class="empty-state">Everything looks good 🎉</div>';
  document.getElementById('bottlenecks-list').innerHTML = html;
}

// ── Auto-refresh ──────────────────────────────────────────────

setInterval(() => {
  const active = document.querySelector('.tab-content.active');
  if (!active) return;
  const name = active.id.replace('tab-', '');
  if (name === 'pulse') loadPulse();
  else if (name === 'health') loadHealth();
}, 30000);

// ── Init ──────────────────────────────────────────────────────

autoConnect();

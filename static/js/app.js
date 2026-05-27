// Mission Control — Main App
let API_BASE = '';
let DEMO_MODE = false;

const API = {
  async get(endpoint) {
    // Try real API first (local or remote)
    if (API_BASE) {
      try {
        const res = await fetch(API_BASE + endpoint);
        if (res.ok) return await res.json();
      } catch (e) {
        console.error(`API ${endpoint} failed:`, e);
      }
    }
    // Fall back to demo data when hosted (no local server available)
    if (DEMO_MODE) return getDemoData(endpoint);
    return null;
  }
};

// ── Demo data (used when deployed to Vercel / no local server) ─

const DEMO_DATA = {
  '/api/status': { status: 'ok', workspace: 'octo-workspace (demo)', mode: 'demo' },
  '/api/tasks': [
    { title: 'Make Mission Control mobile-responsive', source: 'memory/2026-05-26.md', status: 'done' },
    { title: 'Build Task Board kanban with status-based sorting', source: 'projects/mission-control/SPEC.md', status: 'done' },
    { title: 'Wire up all 7 dashboard tabs with real data', source: 'projects/mission-control/SPEC.md', status: 'done' },
    { title: 'Deploy IdeaForge to Vercel with auto-deploy', source: 'memory/2026-05-26.md', status: 'done' },
    { title: 'Study abroad decision — Morocco vs Singapore', source: 'memory/areas/school.md', status: 'todo' },
    { title: 'Set up outreach email for cold outreach', source: 'MEMORY.md', status: 'todo' },
    { title: 'Build Relay product demo with simulation server', source: 'projects/withocto-site/', status: 'progress' },
    { title: 'Polish withocto.co landing page', source: 'projects/withocto-site/', status: 'progress' }
  ],
  '/api/projects': [
    { name: 'withocto-site', path: 'projects/withocto-site/', status: 'active', modified: '2026-05-26T22:00:00', file_count: 24, task_count: 4, has_spec: true },
    { name: 'mission-control', path: 'projects/mission-control/', status: 'active', modified: '2026-05-26T22:10:00', file_count: 15, task_count: 3, has_spec: true },
    { name: 'saas-idea-generator', path: 'projects/saas-idea-generator/', status: 'active', modified: '2026-05-26T21:00:00', file_count: 18, task_count: 2, has_spec: false },
    { name: 'neurobeats', path: 'projects/neurobeats/', status: 'pending', modified: '2026-05-20T00:00:00', file_count: 8, task_count: 0, has_spec: false },
    { name: 'mbsa-site', path: 'projects/mbsa-site/', status: 'pending', modified: '2026-05-24T00:00:00', file_count: 10, task_count: 0, has_spec: false },
    { name: 'AAAS-freelancing', path: 'memory/areas/freelancing.md', status: 'active', modified: '2026-05-19T00:00:00', file_count: 1, task_count: 0, has_spec: false }
  ],
  '/api/memories': {
    daily: [
      { relative: 'memory/2026-05-26.md', name: '2026-05-26.md', size: 5200, modified: '2026-05-26T22:11:00' },
      { relative: 'memory/2026-05-25.md', name: '2026-05-25.md', size: 3100, modified: '2026-05-25T23:00:00' }
    ],
    areas: [
      { relative: 'memory/areas/school.md', name: 'school.md', size: 2800, modified: '2026-05-25T00:00:00' },
      { relative: 'memory/areas/recruiting.md', name: 'recruiting.md', size: 1900, modified: '2026-05-20T00:00:00' },
      { relative: 'memory/areas/content.md', name: 'content.md', size: 1500, modified: '2026-05-18T00:00:00' },
      { relative: 'memory/areas/freelancing.md', name: 'freelancing.md', size: 2100, modified: '2026-05-19T00:00:00' }
    ],
    resources: [
      { relative: 'memory/resources/resume.md', name: 'resume.md', size: 1800, modified: '2026-05-10T00:00:00' },
      { relative: 'memory/resources/tools.md', name: 'tools.md', size: 1200, modified: '2026-05-19T00:00:00' }
    ]
  },
  '/api/docs': [
    { name: 'SPEC', path: 'projects/mission-control/SPEC.md', size: 3846, modified: '2026-05-26T18:25:00' },
    { name: 'PROMPTS', path: 'projects/mission-control/PROMPTS.md', size: 4097, modified: '2026-05-26T18:25:00' },
    { name: 'MEMORY', path: 'MEMORY.md', size: 3800, modified: '2026-05-26T22:00:00' },
    { name: 'AGENTS', path: 'AGENTS.md', size: 13104, modified: '2026-05-19T00:00:00' },
    { name: 'TOOLS', path: 'TOOLS.md', size: 2150, modified: '2026-05-19T00:00:00' }
  ],
  '/api/team': [
    { name: 'Octo Prime', role: 'Main Agent', status: 'active', model: 'deepseek-v4-pro' },
    { name: 'Claude Code', role: 'Dev Sub-agent', status: 'idle', model: 'claude-sonnet-4-6' }
  ],
  '/api/activity': [
    { type: 'md', name: 'Mission Control deployed to Vercel', path: 'projects/mission-control/', modified: '2026-05-26T22:11:00' },
    { type: 'css', name: 'Dashboard CSS — mobile-responsive rewrite', path: 'projects/mission-control/static/css/', modified: '2026-05-26T22:05:00' },
    { type: 'js', name: 'tasks.js — kanban with status-based sorting', path: 'projects/mission-control/static/js/', modified: '2026-05-26T22:03:00' },
    { type: 'json', name: 'IdeaForge deployed to Vercel', path: 'projects/saas-idea-generator/', modified: '2026-05-26T21:30:00' },
    { type: 'js', name: 'saved.ts — localStorage save feature', path: 'projects/saas-idea-generator/src/lib/', modified: '2026-05-26T20:45:00' },
    { type: 'md', name: 'SPEC.md — Mission Control spec written', path: 'projects/mission-control/', modified: '2026-05-26T18:25:00' }
  ],
  '/api/cron': { jobs: [
    { name: 'Heartbeat check — email + calendar', schedule: 'every 30min', cron: '0,30 * * * *' },
    { name: 'Memory consolidation (weekly)', schedule: 'weekly Mon 9am', cron: '0 9 * * 1' },
    { name: 'Daily brief summary', schedule: 'daily 8pm', cron: '0 20 * * *' },
    { name: 'Study abroad deadline reminder', schedule: 'daily 9am', cron: '0 9 * * *' }
  ] }
};

function getDemoData(endpoint) {
  return DEMO_DATA[endpoint] || null;
}

// ── Connection management ─────────────────────────────────────

const apiUrlInput    = document.getElementById('api-url');
const apiConnectBtn  = document.getElementById('api-connect-btn');
const apiLabel       = document.getElementById('api-label');
const apiIndicator   = document.querySelector('.api-indicator');
const statusDot      = document.getElementById('status-dot');
const mobileStatus   = document.getElementById('mobile-status');
const connectionStatus = document.getElementById('connection-status');

function setConnected(workspace) {
  const name = workspace ? workspace.split('/').pop() : 'workspace';
  apiLabel.textContent = `Connected — ${name}`;
  apiIndicator.className = 'api-indicator connected';
  statusDot.className = 'status-dot connected';
  mobileStatus.className = 'connected';
  connectionStatus.textContent = '● Connected';
}

function setDisconnected(msg) {
  apiLabel.textContent = msg || 'Connection failed';
  apiIndicator.className = 'api-indicator disconnected';
  statusDot.className = 'status-dot disconnected';
  mobileStatus.className = 'disconnected';
  connectionStatus.textContent = '● Disconnected';
}

async function connectAPI() {
  const url = apiUrlInput.value.replace(/\/$/, '');
  API_BASE = url;

  apiLabel.textContent = 'Connecting…';
  apiIndicator.className = 'api-indicator disconnected';

  const status = await API.get('/api/status');

  if (status && status.status === 'ok') {
    setConnected(status.workspace);
    // Reload current tab
    const active = document.querySelector('.tab-content.active');
    if (active) {
      const name = active.id.replace('tab-', '');
      const handler = tabLoaders[name];
      if (handler) handler();
    }
  } else {
    API_BASE = '';
    setDisconnected('Connection failed');
  }
}

apiConnectBtn.addEventListener('click', connectAPI);
apiUrlInput.addEventListener('keydown', e => { if (e.key === 'Enter') connectAPI(); });

// Auto-connect on load
connectAPI();

// Auto-demo: if connect fails and we're not on localhost, enable demo mode
setTimeout(() => {
  if (!API_BASE && !window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
    DEMO_MODE = true;
    setConnected('octo-workspace (demo)');
    apiUrlInput.placeholder = 'Demo mode — no server needed';
    const active = document.querySelector('.tab-content.active');
    if (active) {
      const name = active.id.replace('tab-', '');
      const handler = tabLoaders[name];
      if (handler) handler();
    }
  }
}, 1500);

// ── Mobile sidebar ────────────────────────────────────────────

const sidebar         = document.getElementById('sidebar');
const overlay         = document.getElementById('sidebar-overlay');
const hamburger       = document.getElementById('hamburger');

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

hamburger.addEventListener('click', () => {
  sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
});

overlay.addEventListener('click', closeSidebar);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && sidebar.classList.contains('open')) closeSidebar();
});

// ── Tab navigation ────────────────────────────────────────────

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    item.classList.add('active');

    const tab = item.dataset.tab;
    document.getElementById(`tab-${tab}`).classList.add('active');

    const handler = tabLoaders[tab];
    if (handler) handler();

    // Close drawer on mobile after selecting a tab
    if (window.innerWidth < 768) closeSidebar();
  });
});

const tabLoaders = {
  tasks:    loadTasks,
  projects: loadProjects,
  memories: loadMemories,
  docs:     loadDocs,
  calendar: loadCalendar,
  team:     loadTeam,
  office:   loadOffice,
};

// Auto-refresh office every 30s when active
setInterval(() => {
  if (document.getElementById('tab-office').classList.contains('active')) {
    loadOffice();
  }
}, 30000);

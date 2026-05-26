// Mission Control — Main App
let API_BASE = '';

const API = {
  async get(endpoint) {
    if (!API_BASE) return null;
    try {
      const res = await fetch(API_BASE + endpoint);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error(`API ${endpoint} failed:`, e);
      return null;
    }
  }
};

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

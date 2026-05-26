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

// Connection management
const apiUrlInput = document.getElementById('api-url');
const apiConnectBtn = document.getElementById('api-connect-btn');
const apiLabel = document.getElementById('api-label');
const apiIndicator = document.querySelector('.api-indicator');
const statusDot = document.getElementById('status-dot');
const connectionStatus = document.getElementById('connection-status');

async function connectAPI() {
  const url = apiUrlInput.value.replace(/\/$/, '');
  API_BASE = url;
  
  apiLabel.textContent = 'Connecting...';
  apiIndicator.className = 'api-indicator disconnected';
  
  const status = await API.get('/api/status');
  
  if (status && status.status === 'ok') {
    apiLabel.textContent = `Connected — ${status.workspace.split('/').pop()}`;
    apiIndicator.className = 'api-indicator connected';
    statusDot.className = 'status-dot connected';
    connectionStatus.textContent = '● Connected';
    
    // Reload current tab
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab) {
      const tabName = activeTab.id.replace('tab-', '');
      const handler = tabLoaders[tabName];
      if (handler) handler();
    }
  } else {
    apiLabel.textContent = 'Connection failed';
    apiIndicator.className = 'api-indicator disconnected';
    statusDot.className = 'status-dot disconnected';
    connectionStatus.textContent = '● Disconnected';
  }
}

apiConnectBtn.addEventListener('click', connectAPI);
apiUrlInput.addEventListener('keydown', e => { if (e.key === 'Enter') connectAPI(); });

// Auto-connect on load
connectAPI();

// Tab navigation
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    item.classList.add('active');
    const tab = item.dataset.tab;
    document.getElementById(`tab-${tab}`).classList.add('active');
    const handler = tabLoaders[tab];
    if (handler) handler();
  });
});

const tabLoaders = {
  tasks: loadTasks,
  projects: loadProjects,
  memories: loadMemories,
  docs: loadDocs,
  calendar: loadCalendar,
  team: loadTeam,
  office: loadOffice
};

// Auto-refresh office every 30s
setInterval(() => {
  if (document.getElementById('tab-office').classList.contains('active')) {
    loadOffice();
  }
}, 30000);

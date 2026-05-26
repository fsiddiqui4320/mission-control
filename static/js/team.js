// Team / Agent Roster
async function loadTeam() {
  const list = document.getElementById('team-list');
  list.innerHTML = '<div class="loading">Loading team…</div>';

  // Try API first; fall back to defaults
  const data = await API.get('/api/team');
  const agents = (data && data.length) ? data : defaultAgents();

  if (!agents.length) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">👥</div>
        <p>No agents configured</p>
      </div>`;
    return;
  }

  list.innerHTML = agents.map(a => {
    const isActive = a.status === 'active';
    const statusLabel = isActive ? 'Active' : 'Idle';
    return `
      <div class="agent-card">
        <div class="agent-avatar">${a.avatar || '🤖'}</div>
        <div class="agent-info">
          <div class="agent-name">${escapeHtml(a.name)}</div>
          <div class="agent-role">${escapeHtml(a.role)}</div>
          ${a.task ? `<div class="agent-role" style="color:var(--accent);margin-top:2px">↳ ${escapeHtml(a.task)}</div>` : ''}
          <div class="agent-model">${escapeHtml(a.model)}</div>
        </div>
        <div class="agent-status-badge">
          <span class="status-pip ${isActive ? 'active' : 'idle'}"></span>
          <span style="color:var(--text-secondary)">${statusLabel}</span>
        </div>
      </div>`;
  }).join('');
}

function defaultAgents() {
  return [
    {
      name:   'Octo Prime',
      avatar: '🐙',
      role:   'Main orchestration agent',
      status: 'active',
      task:   'Running Mission Control dashboard',
      model:  'deepseek-v4-pro',
    },
    {
      name:   'Claude Code',
      avatar: '🤖',
      role:   'Dev sub-agent',
      status: 'idle',
      task:   null,
      model:  'claude-sonnet-4-6',
    },
  ];
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

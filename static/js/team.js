// Team / Agent Roster
async function loadTeam() {
  const grid = document.getElementById('team-grid');
  
  // For now, render from known agents until real API is wired
  const agents = [
    { name: 'Octo Prime', role: 'Main Agent', status: 'active', model: 'deepseek-v4-pro' },
    { name: 'Claude Code', role: 'Dev Sub-agent', status: 'idle', model: 'claude-sonnet-4-6' },
  ];
  
  grid.innerHTML = agents.map(a => `
    <div class="card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <div style="width:10px;height:10px;border-radius:50%;background:${a.status === 'active' ? 'var(--accent-green)' : 'var(--text-secondary)'}"></div>
        <h3>${a.name}</h3>
      </div>
      <p>${a.role}</p>
      <p style="font-size:11px;color:var(--text-secondary);margin-top:4px">Model: ${a.model}</p>
    </div>
  `).join('');
}

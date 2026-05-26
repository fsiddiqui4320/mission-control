// Memories Browser
let memoriesData = null;

async function loadMemories() {
  const list = document.getElementById('memories-list');
  list.innerHTML = '<div class="loading">Loading memories…</div>';

  memoriesData = await API.get('/api/memories');

  if (!memoriesData) {
    list.innerHTML = '<div class="loading">Connect API to load memories</div>';
    return;
  }

  renderMemories('');
}

function renderMemories(query) {
  const list = document.getElementById('memories-list');
  if (!memoriesData) return;

  const sections = [
    { key: 'daily',     icon: '📅', label: 'Daily Notes' },
    { key: 'areas',     icon: '📂', label: 'Areas' },
    { key: 'resources', icon: '📚', label: 'Resources' },
    { key: 'other',     icon: '📝', label: 'Other' },
  ];

  const q = query.toLowerCase().trim();
  let html = '';
  let totalShown = 0;

  sections.forEach(s => {
    let items = memoriesData[s.key] || [];
    if (q) {
      items = items.filter(m =>
        (m.relative || m.name || '').toLowerCase().includes(q)
      );
    }
    if (!items.length) return;

    totalShown += items.length;
    html += `
      <div class="memory-section">
        <div class="memory-section-header">
          ${s.icon} ${s.label}
          <span class="section-count">${items.length}</span>
        </div>`;

    items.forEach(m => {
      const name = m.relative || m.name || 'Unknown';
      const kb   = m.size ? `${(m.size / 1024).toFixed(1)} KB` : '';
      const date = m.modified ? new Date(m.modified).toLocaleDateString() : '';
      const meta = [kb, date].filter(Boolean).join(' · ');
      html += `
        <div class="memory-item">
          <span class="memory-name" title="${escapeHtml(name)}">${escapeHtml(name)}</span>
          ${meta ? `<span class="memory-meta">${escapeHtml(meta)}</span>` : ''}
        </div>`;
    });

    html += '</div>';
  });

  if (!totalShown) {
    html = q
      ? `<div class="empty-state"><div class="empty-icon">🔍</div><p>No memories match "${escapeHtml(q)}"</p></div>`
      : `<div class="empty-state"><div class="empty-icon">🧠</div><p>No memory files found in workspace</p></div>`;
  }

  list.innerHTML = html;
}

// Wire up search
document.getElementById('memory-search').addEventListener('input', e => {
  renderMemories(e.target.value);
});

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

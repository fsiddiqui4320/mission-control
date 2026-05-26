// Document Library
let docsData = null;

async function loadDocs() {
  const list = document.getElementById('docs-list');
  list.innerHTML = '<div class="loading">Loading documents…</div>';

  docsData = await API.get('/api/docs');

  if (!docsData) {
    list.innerHTML = '<div class="loading">Connect API to load documents</div>';
    return;
  }

  renderDocs('');
}

function renderDocs(query) {
  const list = document.getElementById('docs-list');
  if (!docsData) return;

  const q = query.toLowerCase().trim();
  let items = docsData;
  if (q) {
    items = items.filter(d =>
      (d.name || '').toLowerCase().includes(q) ||
      (d.path || '').toLowerCase().includes(q)
    );
  }

  if (!items.length) {
    list.innerHTML = q
      ? `<div class="empty-state"><div class="empty-icon">🔍</div><p>No documents match "${escapeHtml(q)}"</p></div>`
      : `<div class="empty-state"><div class="empty-icon">📄</div><p>No documents found in workspace</p></div>`;
    return;
  }

  list.innerHTML = items.map(d => {
    const date = d.modified ? new Date(d.modified).toLocaleDateString() : '';
    const kb   = d.size ? `${(d.size / 1024).toFixed(1)} KB` : '';
    const meta = [kb, date].filter(Boolean).join(' · ');
    return `
      <div class="doc-item">
        <span class="doc-icon">📄</span>
        <span class="doc-name" title="${escapeHtml(d.path || d.name)}">${escapeHtml(d.name)}.md</span>
        ${meta ? `<span class="doc-meta">${escapeHtml(meta)}</span>` : ''}
      </div>`;
  }).join('');
}

document.getElementById('docs-search').addEventListener('input', e => {
  renderDocs(e.target.value);
});

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

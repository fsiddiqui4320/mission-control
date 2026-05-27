// Projects
async function loadProjects() {
  const grid = document.getElementById('projects-grid');
  grid.innerHTML = '<div class="loading">Loading projects…</div>';

  const data = await API.get('/api/projects');

  if (!data) {
    grid.innerHTML = '<div class="loading">Connect API to load projects</div>';
    return;
  }

  if (!data.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📁</div>
        <p>No projects found in workspace</p>
      </div>`;
    return;
  }

  grid.innerHTML = data.map(p => {
    const name = p.name.replace(/-/g, ' ').replace(/_/g, ' ');
    const modified = p.modified ? new Date(p.modified) : null;
    const age = modified ? relativeTime(modified) : '';
    const fileCount = p.file_count || 0;
    const taskCount = p.task_count || 0;

    const tags = [];
    if (p.has_spec) tags.push(['📋 Spec', 'green']);
    if (taskCount > 0) tags.push([`${taskCount} task${taskCount !== 1 ? 's' : ''}`, 'blue']);
    if (fileCount > 0) tags.push([`${fileCount} file${fileCount !== 1 ? 's' : ''}`, '']);

    const tagsHtml = tags.map(([label, cls]) =>
      `<span class="meta-tag ${cls}">${label}</span>`
    ).join('');

    return `
      <div class="card">
        <h3>${escapeHtml(capitalise(name))}</h3>
        <p>Modified ${age}</p>
        ${tagsHtml ? `<div class="card-meta">${tagsHtml}</div>` : ''}
      </div>`;
  }).join('');
}

function capitalise(str) {
  return str.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function relativeTime(date) {
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)   return 'just now';
  if (mins < 60)  return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7)   return `${days}d ago`;
  return date.toLocaleDateString();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

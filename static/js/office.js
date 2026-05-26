// Office — Activity Feed
async function loadOffice() {
  const feed = document.getElementById('office-feed');

  const [statusData, activityData] = await Promise.all([
    API.get('/api/status'),
    API.get('/api/activity'),
  ]);

  const items = [];

  if (activityData && activityData.length) {
    activityData.forEach(f => {
      items.push({
        time:  relativeTime(new Date(f.modified)),
        text:  `${fileIcon(f.type)} ${f.name}`,
        path:  f.path,
        cls:   fileClass(f.path),
      });
    });
  }

  // Always show a status line
  if (statusData) {
    items.unshift({
      time: 'Now',
      text: `🟢 Workspace active — ${statusData.workspace || '~/.openclaw/workspace'}`,
      path: null,
      cls:  '',
    });
  } else {
    items.unshift({
      time: 'Now',
      text: '⚠️ Server offline — connect the API to see live activity',
      path: null,
      cls:  '',
    });
  }

  feed.innerHTML = items.map(item => `
    <div class="feed-item ${item.cls}">
      <div class="feed-time">${escapeHtml(item.time)}</div>
      <div class="feed-text">${escapeHtml(item.text)}</div>
      ${item.path ? `<div class="feed-path">${escapeHtml(item.path)}</div>` : ''}
    </div>
  `).join('');

  if (!feed.children.length) {
    feed.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🏢</div>
        <p>No recent activity found</p>
      </div>`;
  }
}

function fileIcon(type) {
  const map = { md: '📝', json: '📋', py: '🐍', js: '📦', ts: '📦', css: '🎨', html: '🌐', txt: '📄' };
  return map[type] || '📄';
}

function fileClass(path) {
  if (!path) return '';
  if (path.includes('/memory/'))   return 'memory';
  if (path.includes('/projects/')) return 'project';
  return 'file';
}

function relativeTime(date) {
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)   return 'Just now';
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

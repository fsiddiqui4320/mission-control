// Memories Browser
async function loadMemories() {
  const list = document.getElementById('memories-list');
  const data = await API.get('/api/memories');
  
  if (!data) {
    list.innerHTML = '<div class="loading">Loading memories...</div>';
    return;
  }
  
  let html = '';
  const sections = [
    { key: 'daily', label: '📅 Daily Notes' },
    { key: 'areas', label: '📂 Areas' },
    { key: 'resources', label: '📚 Resources' },
    { key: 'other', label: '📝 Other' }
  ];
  
  sections.forEach(s => {
    const items = data[s.key];
    if (items && items.length) {
      html += `<div class="memory-section"><h3>${s.label}</h3>`;
      items.forEach(m => {
        html += `
          <div class="memory-item">
            <span>${m.relative || m.name}</span>
            <span class="memory-meta">${(m.size / 1024).toFixed(1)} KB · ${new Date(m.modified).toLocaleDateString()}</span>
          </div>`;
      });
      html += '</div>';
    }
  });
  
  list.innerHTML = html || '<div class="loading">No memory files found</div>';
}

// Document Library
async function loadDocs() {
  const list = document.getElementById('docs-list');
  const data = await API.get('/api/docs');
  
  if (!data || !data.length) {
    list.innerHTML = '<div class="loading">No documents found</div>';
    return;
  }
  
  list.innerHTML = data.map(d => `
    <div class="memory-item">
      <span>📄 ${d.name}.md</span>
      <span class="memory-meta">${(d.size / 1024).toFixed(1)} KB · ${new Date(d.modified).toLocaleDateString()}</span>
    </div>
  `).join('');
}

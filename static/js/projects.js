// Projects
async function loadProjects() {
  const grid = document.getElementById('projects-grid');
  const data = await API.get('/api/projects');
  
  if (!data || !data.length) {
    grid.innerHTML = '<div class="loading">No projects found</div>';
    return;
  }
  
  grid.innerHTML = data.map(p => `
    <div class="card">
      <h3>${p.name}</h3>
      <p>Modified: ${new Date(p.modified).toLocaleDateString()}</p>
      ${p.has_spec ? '<p style="color:var(--accent-green);font-size:12px">📋 Has spec</p>' : ''}
    </div>
  `).join('');
}

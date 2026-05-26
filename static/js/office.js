// Office — Activity Feed
async function loadOffice() {
  const feed = document.getElementById('office-feed');
  
  // Build activity from recent file modifications
  const data = await API.get('/api/status');
  
  feed.innerHTML = `
    <div class="feed-item">
      <div class="feed-time">Just now</div>
      <div>🐙 Octo Prime — Mission Control project initialized</div>
    </div>
    <div class="feed-item">
      <div class="feed-time">${new Date().toLocaleTimeString()}</div>
      <div>📁 Workspace active at ${data?.workspace || '~/.openclaw/workspace'}</div>
    </div>
    <div class="feed-item">
      <div class="feed-time">Ready</div>
      <div>Dashboard server running on localhost:5555</div>
    </div>
  `;
}

// Task Board
function createTaskCard(task) {
  const card = document.createElement('div');
  card.className = 'task-card';

  // Strip leading checkbox/todo markers for cleaner display
  let title = task.title
    .replace(/^-\s*\[[x >/]\]\s*/i, '')
    .replace(/^(TODO|FIXME):?\s*/i, '')
    .trim();

  // Truncate long titles
  const displayTitle = title.length > 120 ? title.slice(0, 120) + '…' : title;

  // Shorten source path
  const parts = task.source.split('/');
  const shortSource = parts.slice(-2).join('/');

  card.innerHTML = `
    <div class="task-title">${escapeHtml(displayTitle)}</div>
    <div class="task-source">
      <span>📂</span>
      <span class="task-source-path" title="${escapeHtml(task.source)}">${escapeHtml(shortSource)}</span>
    </div>
  `;
  return card;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function loadTasks() {
  const todo     = document.getElementById('items-todo');
  const progress = document.getElementById('items-progress');
  const done     = document.getElementById('items-done');

  todo.innerHTML = progress.innerHTML = done.innerHTML = '<div class="loading">Loading…</div>';

  const data = await API.get('/api/tasks');

  if (!data) {
    todo.innerHTML = '<div class="task-empty">Connect API to load tasks</div>';
    progress.innerHTML = done.innerHTML = '';
    updateCounts(0, 0, 0);
    return;
  }

  if (!data.length) {
    todo.innerHTML = '<div class="task-empty">No tasks found in workspace</div>';
    progress.innerHTML = done.innerHTML = '';
    updateCounts(0, 0, 0);
    return;
  }

  todo.innerHTML = progress.innerHTML = done.innerHTML = '';
  let nTodo = 0, nProgress = 0, nDone = 0;

  data.forEach(task => {
    const card = createTaskCard(task);
    if (task.status === 'done') {
      done.appendChild(card);
      nDone++;
    } else if (task.status === 'in_progress') {
      progress.appendChild(card);
      nProgress++;
    } else {
      todo.appendChild(card);
      nTodo++;
    }
  });

  if (!nTodo)     todo.innerHTML = '<div class="task-empty">No open tasks</div>';
  if (!nProgress) progress.innerHTML = '<div class="task-empty">Nothing in progress</div>';
  if (!nDone)     done.innerHTML = '<div class="task-empty">No completed tasks</div>';

  updateCounts(nTodo, nProgress, nDone);
}

function updateCounts(todo, progress, done) {
  document.getElementById('count-todo').textContent = todo;
  document.getElementById('count-progress').textContent = progress;
  document.getElementById('count-done').textContent = done;
}

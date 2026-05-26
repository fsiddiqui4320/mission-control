// Task Board
async function loadTasks() {
  const data = await API.get('/api/tasks');
  const todo = document.querySelector('#col-todo .kanban-items');
  const progress = document.querySelector('#col-progress .kanban-items');
  const done = document.querySelector('#col-done .kanban-items');
  
  if (!data || !data.length) {
    todo.innerHTML = '<div class="loading">No tasks found yet</div>';
    return;
  }
  
  todo.innerHTML = '';
  progress.innerHTML = '';
  done.innerHTML = '';
  
  data.forEach((task, i) => {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.innerHTML = `
      <div>${task.title}</div>
      <div class="task-source">${task.source}</div>
    `;
    // Distribute: first few to todo, some to progress
    if (i < Math.ceil(data.length / 2)) {
      todo.appendChild(card);
    } else if (i < Math.ceil(data.length * 0.8)) {
      progress.appendChild(card);
    } else {
      done.appendChild(card);
    }
  });
}

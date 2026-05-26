// Calendar View
async function loadCalendar() {
  const grid = document.getElementById('calendar-grid');
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  
  let html = `<h3 style="margin-bottom:16px">${monthNames[month]} ${year}</h3>`;
  html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;text-align:center">';
  ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => {
    html += `<div style="font-size:12px;color:var(--text-secondary);padding:8px">${d}</div>`;
  });
  
  for (let i = 0; i < firstDay; i++) html += '<div></div>';
  for (let day = 1; day <= daysInMonth; day++) {
    const isToday = day === now.getDate();
    const style = isToday ? 'background:var(--accent);color:#fff;font-weight:600' : 'background:var(--bg-secondary)';
    html += `<div style="padding:8px;border-radius:6px;${style};font-size:13px">${day}</div>`;
  }
  html += '</div>';
  
  grid.innerHTML = html;
}

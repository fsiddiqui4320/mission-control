// Calendar View
const MONTH_NAMES = ['January','February','March','April','May','June',
                     'July','August','September','October','November','December'];

let calYear, calMonth;

async function loadCalendar() {
  const grid = document.getElementById('calendar-grid');
  const now  = new Date();

  if (calYear === undefined) {
    calYear  = now.getFullYear();
    calMonth = now.getMonth();
  }

  // Load cron data for event markers
  const cronData = await API.get('/api/cron');
  const jobs = cronData?.jobs || [];

  renderCalendar(grid, now, jobs);
}

function renderCalendar(container, now, jobs) {
  const firstDay    = new Date(calYear, calMonth, 1).getDay();
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  const isCurrentMonth = calYear === now.getFullYear() && calMonth === now.getMonth();

  let html = `
    <div class="cal-header">
      <button class="cal-nav-btn" id="cal-prev">‹</button>
      <h3>${MONTH_NAMES[calMonth]} ${calYear}</h3>
      <button class="cal-nav-btn" id="cal-next">›</button>
    </div>
    <div class="calendar-wrapper">
      <div class="cal-grid">
  `;

  // Day labels
  ['Su','Mo','Tu','We','Th','Fr','Sa'].forEach(d => {
    html += `<div class="cal-day-label">${d}</div>`;
  });

  // Empty cells before first day
  for (let i = 0; i < firstDay; i++) {
    html += '<div class="cal-day empty"></div>';
  }

  // Day cells
  for (let day = 1; day <= daysInMonth; day++) {
    const isToday = isCurrentMonth && day === now.getDate();
    const hasEvent = jobs.some(j => matchesCronDay(j, calYear, calMonth, day));
    const cls = ['cal-day', isToday && 'today', hasEvent && 'has-event']
      .filter(Boolean).join(' ');
    html += `<div class="${cls}">${day}</div>`;
  }

  html += '</div></div>';

  // Cron jobs section
  if (jobs.length) {
    html += `<div class="cron-section">
      <div class="cron-section-title">Scheduled Jobs (${jobs.length})</div>`;
    jobs.forEach(j => {
      html += `
        <div class="cron-item">
          <span class="cron-schedule">${escapeHtml(j.schedule || j.cron || '—')}</span>
          <span class="cron-label">${escapeHtml(j.name || j.label || j.command || 'Unnamed job')}</span>
        </div>`;
    });
    html += '</div>';
  } else {
    html += `<div class="cron-section">
      <div class="cron-section-title">Scheduled Jobs</div>
      <div class="cron-item"><span class="cron-label" style="color:var(--text-secondary);font-style:italic">No cron jobs found — start server to load</span></div>
    </div>`;
  }

  container.innerHTML = html;

  document.getElementById('cal-prev').addEventListener('click', () => {
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    renderCalendar(container, new Date(), jobs);
  });

  document.getElementById('cal-next').addEventListener('click', () => {
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    renderCalendar(container, new Date(), jobs);
  });
}

function matchesCronDay(job, year, month, day) {
  // Simple: if cron schedule contains the day number, treat as event (rough heuristic)
  const sched = job.schedule || job.cron || '';
  return sched.includes(String(day)) && day <= 7;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

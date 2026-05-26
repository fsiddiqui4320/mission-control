# Mission Control — Build Prompts

Key prompts from Alex Finn's approach. The core technique is "reverse prompting" — using OpenClaw to build tools that visualize OpenClaw's own state.

## Architecture Prompt (master build prompt)

Send this to Claude Code (or ChatGPT/OpenClaw) to scaffold the entire dashboard:

```
Build me a local Mission Control dashboard for my OpenClaw AI agent system. This is a single-page HTML application with a Python backend that visualizes everything my AI agents are doing.

THE DASHBOARD HAS 7 TABS:

1. TASK BOARD — Kanban (To Do / In Progress / Done). Reads from workspace task tracking files. Each task shows: title, assigned agent, priority, deadline, status.

2. CALENDAR — Weekly/monthly view showing scheduled cron jobs, deadlines, and reminders. Reads from ~/.openclaw/workspace/ files and cron configuration.

3. PROJECTS — Cards for each active project in ~/.openclaw/workspace/projects/. Shows project name, status, linked memory files, recent activity.

4. MEMORIES — Searchable browser of all memory files (~/.openclaw/workspace/memory/). Shows daily notes, area files, resources. Preview on click.

5. DOCS — Library of all generated markdown documents across the workspace. Filterable by project. Shows last modified date.

6. TEAM — Agent roster showing each configured agent/sub-agent. Displays: name, role, status (active/idle), current task, model being used.

7. OFFICE — Visual activity feed showing recent agent actions. Think "who's in the office right now" — which agents are active, what they're doing.

TECHNICAL REQUIREMENTS:
- Single HTML file (index.html) with vanilla JS (no React, no framework)
- Python backend (Flask) that serves the HTML and provides JSON API endpoints
- All data read LIVE from the filesystem (~/.openclaw/workspace/)
- Dark theme, clean design — think Linear.app meets terminal
- Tab-based navigation on the left sidebar
- No external database — filesystem is the source of truth
- Must work on macOS, served on localhost:5555

FILE STRUCTURE:
mission-control/
├── index.html
├── server.py
├── static/
│   ├── css/dashboard.css
│   └── js/
│       ├── app.js
│       ├── tasks.js
│       ├── calendar.js
│       ├── projects.js
│       ├── memories.js
│       ├── docs.js
│       ├── team.js
│       └── office.js
└── SPEC.md

Build all of this. Start with the Python server and the HTML shell, then implement each tab one at a time.
```

## Tab-Specific Prompts

### Task Board
```
Add a Kanban task board to the mission control dashboard. Three columns: To Do, In Progress, Done. Tasks should be draggable between columns. Read tasks from the workspace filesystem — look for TODO markers, task tracking files, and active session states. Each task card shows: title, project tag, priority color, and assigned agent avatar.
```

### Calendar
```
Add a calendar view showing all scheduled cron jobs and upcoming deadlines. Pull from OpenClaw's cron configuration and any deadline-tracked files in the workspace. Show as a monthly grid with events listed per day. Today's date highlighted.
```

### Team / Agents
```
Add a Team tab showing all configured agents. Each agent card shows: name, role, status indicator (green=active, gray=idle), current task if any, and model being used. Pull from OpenClaw's agent configuration and active session data.
```

### Office (Activity Feed)
```
Add an Office tab — a live activity feed showing recent agent actions. Think Slack #general but for AI agents. Show timestamp, agent name, action description. Pull from recent session logs and activity files. Auto-refresh every 30 seconds.
```

## Reverse Prompting Technique

Alex Finn's key insight: use OpenClaw to prompt ITSELF to build tools.

1. Send the master build prompt to Claude Code
2. Claude Code builds the dashboard HTML/CSS/JS + Python server
3. Test locally, iterate with targeted prompts for each tab
4. The dashboard then reads OpenClaw's own workspace — closing the loop

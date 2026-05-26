# Mission Control — Implementation Spec

> Based on Alex Finn's OpenClaw Mission Control dashboard
> Source: https://www.youtube.com/watch?v=RhLpV6QDBFE

## What It Is

A local single-page dashboard that visualizes Octo's entire operational state — tasks, calendar, projects, memories, docs, team, and agent activity — all from the workspace files. No VPS needed, runs locally on Mac.

## Tabs / Screens

### 1. Task Board (0:35)
- Kanban-style: To Do / In Progress / Done
- Pulls from workspace task files + active session states
- Shows what Octo is working on right now

### 2. Calendar (3:57)
- Visual calendar showing scheduled cron jobs, deadlines, reminders
- Reads from OpenClaw's cron job list + calendar files
- Confirms Octo is proactively scheduling work

### 3. Projects (5:10)
- Lists all active projects from `/workspace/projects/`
- Each project links to its tasks, memory files, and docs
- Status indicators per project

### 4. Memories (7:03)
- Searchable view of all memory files
- Organized by type: daily notes, areas, resources
- Quick-lookup interface

### 5. Docs (8:29)
- Library of generated documents (specs, plans, content)
- Pulls from workspace markdown files
- Filterable by project/type

### 6. Team (10:29)
- Visual roster of agents and sub-agents
- Role, status, current task per agent
- Session activity indicators

### 7. Office (12:44)
- Visual representation of agent activity
- Shows who's "in the office" (active) vs idle
- Activity feed

## Architecture

```
mission-control/
├── index.html          # Main dashboard (single-page app)
├── server.py           # Lightweight Python file server + API
├── api/
│   └── routes.py       # Endpoints that read workspace files
├── static/
│   ├── css/
│   │   └── dashboard.css
│   └── js/
│       ├── app.js      # Main app logic
│       ├── tasks.js    # Task board logic
│       ├── calendar.js # Calendar view
│       ├── projects.js # Projects view
│       ├── memories.js # Memory browser
│       ├── docs.js     # Document library
│       ├── team.js     # Agent roster
│       └── office.js   # Activity visualization
└── SPEC.md             # This file
```

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS (no framework — keep it lightweight)
- **Backend:** Python (Flask or SimpleHTTP server) — reads filesystem, serves JSON API
- **Styling:** Clean, dark theme, terminal-inspired but modern
- **No database** — reads directly from workspace filesystem

## Key Design Decisions

1. **Local-first** — runs on Mac, not VPS. Accessible via localhost.
2. **Filesystem as source of truth** — no sync, no duplication. Reads Octo's actual workspace.
3. **Read-only dashboard** — displays state, doesn't modify it (initially).
4. **Single HTML file** with tab navigation — fast, no build step.

## Implementation Phases

### Phase 1: Scaffold (today)
- [ ] Create project structure
- [ ] Build the Python file server with workspace API endpoints
- [ ] Create HTML shell with tab navigation
- [ ] Wire up basic tab switching

### Phase 2: Core Tabs
- [ ] Task Board — read from workspace, render kanban
- [ ] Projects — scan `/workspace/projects/`
- [ ] Memories — scan `/workspace/memory/`
- [ ] Docs — scan for generated docs

### Phase 3: Live Tabs
- [ ] Team — scan agent configs, session states
- [ ] Calendar — scan cron jobs, deadlines
- [ ] Office — activity visualization, live-ish feed

### Phase 4: Polish
- [ ] Dark theme, responsive design
- [ ] Search across all tabs
- [ ] Mobile-friendly
- [ ] Performance optimization

## Discord Channel

Needs a dedicated channel under PROJECTS category.
Suggested name: `#mission-control`
This is where build progress, decisions, and demos go.

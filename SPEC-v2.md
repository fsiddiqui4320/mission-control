# Mission Control v2 — Implementation Spec

> **Principle:** Every tab answers a question Faris actually asks about Octo's operation.
> Not "here's a list of files" — "here's what's happening, what needs attention, and what you can do."

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Vercel (static frontend)                               │
│  Single-page HTML/JS/CSS — deployed via git push        │
│  Connects to: mc-api via Cloudflare Tunnel               │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS (Cloudflare Tunnel)
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MacBook Pro (Python API server + Gateway bridge)       │
│                                                         │
│  server.py  ──┬── Filesystem reader (projects, memory)  │
│               ├── Gateway WS client (sessions, cron,    │
│               │   health, usage, agents)                 │
│               └── REST API → frontend consumes JSON     │
│                                                         │
│  Gateway WS bridge:                                     │
│  - Connects to ws://127.0.0.1:18789 as backend client  │
│  - Authenticates with gateway.auth.token                │
│  - Subscribes to sessions.list, health, usage.status    │
│  - Maintains local state cache                          │
│  - Auto-reconnects with exponential backoff             │
│  - Exposes state via REST endpoints                     │
└─────────────────────────────────────────────────────────┘
```

### Why this architecture

1. **Gateway WS connection lives in the server, not the browser** — the frontend is static HTML on Vercel. WebSocket from browser to Gateway would require exposing the Gateway port publicly (bad) or tunneling. The server is on the same machine as the Gateway, so it can connect directly.

2. **Server aggregates multiple data sources** — filesystem + Gateway WS + external APIs → unified REST API. Frontend only talks to one thing.

3. **State cache in the server** — the Gateway WS connection provides live updates, but if it drops, the server serves cached state with a "stale" indicator rather than nothing.

4. **Single Python file, no framework** — same as now. `http.server` is fine for this. No need for Flask/FastAPI dependency.

---

## Data Sources

### 1. Gateway WebSocket (live operational state)
- **Endpoint:** `ws://127.0.0.1:18789`
- **Auth:** `gateway.auth.token` from openclaw.json
- **Client identity:** `client.id: "mission-control"`, `client.mode: "backend"`
- **Available data:**
  - `sessions.list` → active/recent sessions with agent, surface, activity timestamps
  - `health` → gateway health + per-channel connectivity status
  - `usage.status` → provider usage windows, remaining quota
  - `channels.status` → Discord, Telegram, etc. connection status
  - `config.get` → current config snapshot (for agent roster, cron config)
  - `sessions.subscribe` → real-time session change events

### 2. Filesystem (configuration & knowledge)
- Projects: `/workspace/projects/` — scan with `safe_walk`, read SPEC.md, git status
- Memory: `/workspace/memory/` — daily notes, areas, resources
- Config: `~/.openclaw/openclaw.json` — agent config, cron jobs, channel config
- Blockers: extract from MEMORY.md + project task files

### 3. External (future)
- GitHub status per project (PRs, recent commits)
- Gmail digest
- Calendar events

---

## REST API Endpoints

All endpoints return JSON. The server adds `cached_at` and `source` fields to every response so the frontend knows freshness.

```
GET /api/status         → { ok, gateway: { connected, version }, uptime, cached_at }
GET /api/pulse           → { active_sessions[], recent_activity[], agent_status }
GET /api/projects        → { projects: [{ name, path, last_modified, git_status, tasks, is_active }] }
GET /api/cron            → { jobs: [{ name, schedule, last_run, next_run, last_status }] }
GET /api/health          → { gateway, channels: { discord, telegram }, tunnel, usage }
GET /api/memories        → { daily[], areas[], resources[], search }
GET /api/bottlenecks     → { blockers[], deadlines[], stale_projects[] }
GET /api/actions          → { available_actions[] } — what the user can trigger
POST /api/actions/trigger → { action: "cron:run", job_id: "..." }
```

### Response format
```json
{
  "ok": true,
  "data": { ... },
  "meta": {
    "cached_at": "2026-05-28T03:00:00Z",
    "source": "gateway",  // "gateway" | "filesystem" | "cache" | "error"
    "stale": false
  }
}
```

---

## Tabs & What They Show

### 1. Pulse (home screen)
**Question:** What's Octo doing right now?

- **Active sessions** — which Discord channels have recent activity, with timestamps
- **Current model** — which model is the main agent using, current usage spend
- **Recent activity** — last 10 events (session started, cron ran, file modified, memory written)
- **Agent status** — Octo Prime status (idle/active), last activity time
- **Quick glance numbers** — active sessions count, cron jobs due soon, unread flags

### 2. Projects
**Question:** What's moving forward? What's stalled?

- Each project shows: name, last activity date, git status (clean/dirty/unpushed), spec exists?
- Stale indicator: ⚠️ if no activity in 7+ days
- Active indicator: 🟢 if modified in last 24h
- Click to expand: recent file changes, task count
- Sortable by: recently active, alphabetical, task count

### 3. Cron & Scheduled
**Question:** What's scheduled? Did it run?

- Every cron job: name, schedule (human readable), last run time, last status
- Visual indicators: 🟢 success, 🔴 failed, 🟡 never run, ⏳ running
- **Trigger button** — run a job now (with confirmation)
- Shows next 3 upcoming runs

### 4. Health
**Question:** Is everything running? What's it costing?

- Gateway: connected ✅/disconnected ❌, uptime
- Discord: connected ✅ (with last heartbeat time)
- Telegram: connected ✅
- Tunnel: URL + status
- API usage: current spend (this month), remaining quota
- Memory: workspace size, session count

### 5. Memory
**Question:** What do we know about X?

- Search bar 🔍 across all memory files
- Recent daily notes (last 7 days) with preview
- Area files: quick jump to school, recruiting, freelancing, content
- Each entry shows: filename, modified date, size, first 2 lines preview

### 6. Bottlenecks & Deadlines
**Question:** What needs Faris's attention RIGHT NOW?

- **Persistent blockers** — extracted from MEMORY.md "Persistent Blockers" section
- **Upcoming deadlines** — study abroad (early June!), any calendar events
- **Stale projects** — no activity in 14+ days
- **Failed cron jobs** — any job that errored on last run
- Each item has: severity (🔴 critical, 🟡 warning), age (how many days), action hint

### 7. Quick Actions
**Question:** What can I do from here?

- Trigger a specific cron job
- Run a health check
- Wake/ping a channel
- Clear/sync state

---

## Gateway WebSocket Bridge Design

### Connection lifecycle
```
startup → connect to Gateway WS → authenticate → subscribe to sessions
    ↓
on session event → update local cache → (frontend polls REST, gets fresh data)
    ↓
on disconnect → exponential backoff (1s, 2s, 4s, 8s, max 30s) → reconnect
    ↓
on health event → update health cache
```

### State cache
The server maintains in-memory state objects:
```python
gateway_state = {
    "sessions": [],        # from sessions.list
    "health": {},          # from health RPC
    "channels": {},        # from channels.status
    "usage": {},           # from usage.status
    "cron_jobs": [],       # from config.get → extract cron
    "connected": False,    # WS connection status
    "last_update": None,   # timestamp
}
```

### Error handling
- Gateway unreachable → serve cached state with `stale: true`
- Gateway auth failure → log error, serve filesystem-only data
- Filesystem read error → graceful skip, don't crash
- All API responses include `ok` boolean

---

## Frontend Design

### Constraints
- **Single HTML file** — no framework, no build step. Loads fast on mobile.
- **Dark theme** — existing dashboard CSS, keep the terminal-inspired look
- **Mobile-first** — hamburger sidebar, responsive cards
- **Progressive enhancement** — works without JS (sort of), full features with JS

### Interaction patterns
- Tab navigation (same as now, but different tabs)
- Click to expand/collapse cards
- Search/filter inputs with live results
- Manual refresh button (auto-refreshes every 30s for Pulse/Health)
- Toast notifications for action confirmations

### State indicators
```
🟢 Connected / Active / Success
🟡 Warning / Stale / Degraded
🔴 Error / Disconnected / Failed
⏳ Loading / In Progress
⚪ Idle / Inactive
```

---

## Implementation Plan

### Phase 1: Gateway Bridge (server-side)
- [ ] Read gateway token from openclaw.json
- [ ] WebSocket client connecting to ws://127.0.0.1:18789
- [ ] Authenticate as backend client
- [ ] Call sessions.list, health, usage.status, channels.status
- [ ] Subscribe to session events
- [ ] Maintain state cache
- [ ] Auto-reconnect with backoff

### Phase 2: REST API endpoints
- [ ] /api/status — gateway connection + server info
- [ ] /api/pulse — sessions + activity aggregation
- [ ] /api/projects — filesystem scan (carry forward from v1)
- [ ] /api/cron — from config + gateway state
- [ ] /api/health — gateway health + channels + usage
- [ ] /api/memories — filesystem scan (carry forward from v1)
- [ ] /api/bottlenecks — extracted from MEMORY.md
- [ ] /api/actions — available actions
- [ ] POST /api/actions/trigger — trigger actions

### Phase 3: Frontend rebuild
- [ ] New tab structure (7 tabs)
- [ ] Pulse tab — sessions, activity, quick stats
- [ ] Projects tab — enhanced with git status, staleness
- [ ] Cron tab — job list with trigger buttons
- [ ] Health tab — gateway, channels, usage, tunnel
- [ ] Memory tab — carry forward, add search
- [ ] Bottlenecks tab — blockers, deadlines, failed jobs
- [ ] Quick Actions tab — action buttons

### Phase 4: Polish
- [ ] Auto-refresh with visual indicators
- [ ] Error states for every tab
- [ ] Loading skeletons
- [ ] Mobile responsive pass
- [ ] PWA manifest for installable app

---

## Anti-Patterns to Avoid

1. **❌ Don't poll the Gateway in a loop from the frontend** — the server holds the WS connection, frontend polls REST only
2. **❌ Don't crash if Gateway is down** — serve cached/stale data, show degraded state
3. **❌ Don't hardcode the Gateway token in the server code** — read from openclaw.json at startup
4. **❌ Don't block the server on slow filesystem operations** — use the safe_walk from v1
5. **❌ Don't embed secrets in API responses** — redact tokens, paths, personal info
6. **❌ Don't make the frontend depend on Gateway WS** — REST only for the browser
7. **❌ Don't use rglob on workspace root** — always use safe_walk with SKIP_DIRS
8. **❌ Don't add Python dependencies** — stdlib only (http.server, json, asyncio/websockets? or sync ws with threading)

### Python WebSocket approach
Python's stdlib doesn't have a WebSocket client. Options:
- **websocket-client** (pip install) — simple, synchronous, well-maintained
- **websockets** (pip install) — async, more complex
- **Raw socket + handshake** — don't do this, it's fragile

**Decision:** Use `websocket-client` (sync). It's the simplest approach for a single-connection server. Install via pip. The server already requires Python, so one dependency is fine.

### Threading
The WebSocket connection needs to run in a background thread since `HTTPServer` is blocking. Simple approach:
- Main thread: HTTP server
- Background thread: Gateway WS client, updates shared state (thread-safe with locks)
- REST handlers read from shared state

---

## Success Criteria

1. **Pulse tab shows actual live session data from the Gateway** — not demo data
2. **Cron tab shows real cron jobs with last run status** — with manual trigger working
3. **Health tab turns red when Discord/Gateway is down** — not just showing "connected" always
4. **Bottlenecks tab surfaces the study abroad deadline** — actual actionable items
5. **Frontend works on mobile** — tested at 390px width
6. **Server survives Gateway restart** — reconnects, no crash
7. **Tunnel stays up through reboots** — launchd handles this
8. **Zero hardcoded demo data** — everything comes from real sources or shows empty/error state

---

## File Structure

```
mission-control/
├── server.py              # Main server: HTTP + Gateway WS bridge
├── gateway_bridge.py      # Gateway WebSocket client module
├── api/
│   ├── __init__.py
│   ├── pulse.py           # /api/pulse handler
│   ├── projects.py        # /api/projects handler
│   ├── cron.py            # /api/cron handler
│   ├── health.py          # /api/health handler
│   ├── memories.py        # /api/memories handler
│   ├── bottlenecks.py     # /api/bottlenecks handler
│   └── actions.py         # /api/actions handler
├── static/
│   ├── css/
│   │   └── dashboard.css
│   └── js/
│       ├── app.js         # Main app + tab navigation + API client
│       ├── pulse.js
│       ├── projects.js
│       ├── cron.js
│       ├── health.js
│       ├── memories.js
│       ├── bottlenecks.js
│       └── actions.js
├── index.html
├── scripts/
│   ├── run-tunnel.sh      # (carry forward)
│   ├── capture-tunnel-url.sh
│   └── launchd-wrapper.sh
├── logs/                  # Runtime logs
├── SPEC.md               # This file
└── vercel.json
```

---

## Notes

- The Gateway token is at `gateway.auth.token` in openclaw.json (currently: `f4146b49...`)
- Gateway mode is `local`, bind is `loopback` — only accessible from this machine
- Discord is the primary channel surface — channel health monitoring is critical
- The tunnel URL changes on reboot; the discovery mechanism (GitHub API → tunnel-url.txt) works
- Claude Code will be used for all code generation per workspace rules

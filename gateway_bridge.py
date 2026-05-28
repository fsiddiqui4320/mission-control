"""
Gateway Bridge — reads operational state from filesystem + HTTP health check.
No CLI dependency — pure file reads, can never hang.
Polls periodically in a background thread, updates shared state cache.
"""
import json
import time
import threading
import logging
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("gateway_bridge")

HOME = Path.home()
SESSIONS_FILE = HOME / ".openclaw" / "agents" / "main" / "sessions" / "sessions.json"
CRON_JOBS_FILE = HOME / ".openclaw" / "cron" / "jobs.json"
CRON_STATE_FILE = HOME / ".openclaw" / "cron" / "jobs-state.json"
CONFIG_FILE = HOME / ".openclaw" / "openclaw.json"
GATEWAY_HEALTH_URL = "http://127.0.0.1:18789/health"


class GatewayState:
    """Thread-safe cache of Gateway state."""

    def __init__(self):
        self._lock = threading.Lock()
        self.sessions = []
        self.health = {}
        self.channels = {}
        self.usage = {}
        self.cron_jobs = []
        self.connected = False
        self.version = None
        self.last_update = None
        self.connect_time = None
        self.error = None

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self.last_update = datetime.now(timezone.utc).isoformat()

    def snapshot(self):
        with self._lock:
            return {
                "sessions": list(self.sessions),
                "health": dict(self.health),
                "channels": dict(self.channels),
                "usage": dict(self.usage),
                "cron_jobs": list(self.cron_jobs),
                "connected": self.connected,
                "version": self.version,
                "last_update": self.last_update,
                "connect_time": self.connect_time,
                "error": self.error,
            }


def _read_json(path, default=None):
    """Safely read a JSON file."""
    try:
        if not path.exists():
            return default
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"Failed to read {path}: {e}")
        return default


def _check_health():
    """Check gateway health via HTTP."""
    try:
        req = urllib.request.Request(GATEWAY_HEALTH_URL)
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _parse_sessions_file(data):
    """Parse sessions.json dict into frontend-friendly format."""
    sessions = []
    if not isinstance(data, dict):
        return sessions

    now_ms = int(time.time() * 1000)

    for session_key, s in data.items():
        if not isinstance(s, dict):
            continue

        updated = s.get("updatedAt", 0)
        age_ms = now_ms - updated if updated else 999999999
        age_seconds = max(0, age_ms // 1000)

        if age_seconds < 60:
            age = "just now"
        elif age_seconds < 3600:
            age = f"{age_seconds // 60}m ago"
        elif age_seconds < 86400:
            age = f"{age_seconds // 3600}h ago"
        else:
            age = f"{age_seconds // 86400}d ago"

        # Determine kind and surface from the key pattern
        key_lower = session_key.lower()
        if "cron" in key_lower:
            kind = "cron"
            surface = "cron"
        elif "subagent" in key_lower or "subag" in key_lower:
            kind = "spawn-child"
            surface = "subagent"
        elif "discord" in key_lower:
            kind = "group"
            surface = "discord"
        elif "telegram" in key_lower or "teleg" in key_lower:
            kind = "group" if "group" in key_lower else "direct"
            surface = "telegram"
        elif "heartbeat" in key_lower:
            kind = "heartbeat"
            surface = "heartbeat"
        elif ":main" in session_key.lower():
            kind = "direct"
            surface = "direct"
        else:
            kind = ""
            surface = "unknown"

        # Extract channel ID from discord keys
        channel = ""
        if "discord:channel:" in session_key:
            channel = session_key.split("discord:channel:")[-1][:20]

        # Get human-readable label
        label = s.get("label", "")

        sessions.append({
            "key": session_key[:80],
            "kind": kind,
            "age": age,
            "age_seconds": age_seconds,
            "model": "",
            "surface": surface,
            "channel": channel,
            "runtime": "",
            "tokens_used": 0,
            "token_limit": 0,
            "token_pct": 0,
            "flags": label,
            "status": "active" if age_seconds < 3600 else "idle",
        })

    sessions.sort(key=lambda s: s.get("age_seconds", 999999))
    return sessions[:50]


def _parse_cron_from_state():
    """Build cron job list from jobs.json + jobs-state.json."""
    jobs_data = _read_json(CRON_JOBS_FILE, {})
    state_data = _read_json(CRON_STATE_FILE, {})

    raw_jobs = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else []
    job_states = state_data.get("jobs", {}) if isinstance(state_data, dict) else {}

    now_ms = int(time.time() * 1000)
    result = []

    for j in raw_jobs:
        job_id = j.get("id", "")
        name = j.get("name", j.get("description", job_id[:8]))
        enabled = j.get("enabled", True)
        schedule = j.get("schedule", {})

        # Human-readable schedule
        sk = schedule.get("kind", "cron")
        if sk == "cron":
            schedule_text = schedule.get("expr", "")
        elif sk == "every":
            em = schedule.get("everyMs", 0)
            if em >= 3600000:
                schedule_text = f"every {em // 3600000}h"
            elif em >= 60000:
                schedule_text = f"every {em // 60000}m"
            else:
                schedule_text = f"every {em // 1000}s"
        else:
            schedule_text = sk

        # State
        st = job_states.get(job_id, {}).get("state", {})
        last_run = st.get("lastRunAtMs")
        next_run = st.get("nextRunAtMs")
        last_status = st.get("lastRunStatus", st.get("lastStatus", ""))
        consecutive = st.get("consecutiveErrors", 0)
        last_error = st.get("lastError", "")

        # Determine status indicator
        if not enabled:
            display_status = "disabled"
        elif last_status == "error" or consecutive > 0:
            display_status = "error_recent" if consecutive < 3 else "error"
        elif last_status == "ok":
            display_status = "ok"
        elif last_run is None:
            display_status = "never_run"
        else:
            display_status = last_status or "unknown"

        result.append({
            "id": job_id,
            "name": name,
            "enabled": enabled,
            "schedule": schedule_text,
            "schedule_raw": schedule,
            "last_run": last_run,
            "next_run": next_run,
            "last_status": display_status,
            "last_error": last_error[:200] if last_error else "",
            "consecutive_errors": consecutive,
            "delivery_channel": "",
            "delivery_to": "",
        })

    return result


def fetch_all(state: GatewayState):
    """Fetch all state from filesystem + HTTP health check."""
    try:
        # Gateway health check (HTTP, fast)
        health = _check_health()
        state.update(
            connected=health.get("ok", False),
            health={"gateway_ok": health.get("ok"), "status": health.get("status")},
        )
    except Exception as e:
        state.update(connected=False, error=str(e)[:100])

    try:
        # Sessions from file
        sessions_raw = _read_json(SESSIONS_FILE)
        if sessions_raw:
            sessions = _parse_sessions_file(sessions_raw)
            state.update(sessions=sessions)
        else:
            state.update(sessions=[])
    except Exception as e:
        logger.debug(f"Sessions read error: {e}")

    try:
        # Cron from state files
        cron_jobs = _parse_cron_from_state()
        if cron_jobs:
            state.update(cron_jobs=cron_jobs)
    except Exception as e:
        logger.debug(f"Cron read error: {e}")


class GatewayPoller:
    """Periodically reads state from filesystem."""

    def __init__(self, state: GatewayState, interval: int = 30):
        self.state = state
        self.interval = interval
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="gateway-poller")
        self._thread.start()
        logger.info(f"Gateway poller started (interval={self.interval}s)")

    def stop(self):
        self._running = False

    def _run_loop(self):
        fetch_all(self.state)
        while self._running:
            time.sleep(self.interval)
            if not self._running:
                break
            try:
                fetch_all(self.state)
            except Exception as e:
                logger.error(f"Poller error: {e}")


# ── Singleton ─────────────────────────────────────────────────

_state_instance = None
_poller_instance = None


def get_state() -> GatewayState:
    global _state_instance
    if _state_instance is None:
        _state_instance = GatewayState()
    return _state_instance


def start_bridge(interval: int = 30):
    global _poller_instance
    state = get_state()
    if _poller_instance is None:
        _poller_instance = GatewayPoller(state, interval=interval)
    _poller_instance.start()
    return _poller_instance


def stop_bridge():
    global _poller_instance
    if _poller_instance:
        _poller_instance.stop()
        _poller_instance = None

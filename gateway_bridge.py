"""
Gateway Bridge — polls OpenClaw's CLI for live operational data.
Uses `openclaw sessions`, `openclaw cron list`, `openclaw status --json`.
Runs in a background thread, updates shared state cache.
More robust than direct WS — no auth negotiation, same data, always available.
"""
import json
import re
import time
import threading
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("gateway_bridge")


# ── State cache (thread-safe) ──────────────────────────────────

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
        """Return a thread-safe copy of the state."""
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


# ── Data fetchers ─────────────────────────────────────────────

def _run_cli(args, timeout=10):
    """Run an openclaw CLI command and return parsed output."""
    try:
        result = subprocess.run(
            ["openclaw"] + args,
            capture_output=True, text=True, timeout=timeout,
            env={**__import__('os').environ, "OPENCLAW_NO_COLOR": "1"}
        )
        if result.returncode != 0:
            logger.warning(f"openclaw {' '.join(args)} failed: {result.stderr.strip()[:100]}")
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        logger.error("openclaw CLI not found")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"openclaw {' '.join(args)} timed out")
        return None
    except Exception as e:
        logger.error(f"openclaw {' '.join(args)} error: {e}")
        return None


def _parse_sessions(raw):
    """Parse `openclaw sessions` output (fixed-width table) into structured data."""
    sessions = []
    if not raw:
        return sessions

    lines = raw.split("\n")
    in_table = False
    col_starts = None
    
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("Sessions listed:") or line.startswith("Session store:"):
            continue
        
        # Header row — determine column positions from the separator gaps
        if line.startswith("Kind"):
            in_table = True
            # Find column starts by scanning for transitions: space→non-space after multiple spaces
            col_starts = []
            prev_char = ' '
            gap_count = 0
            for i, ch in enumerate(line):
                if ch == ' ':
                    gap_count += 1
                else:
                    if gap_count >= 2 and prev_char == ' ':
                        col_starts.append(i)
                    gap_count = 0
                prev_char = ch
            if not col_starts or col_starts[0] != 0:
                col_starts.insert(0, 0)
            continue
        
        if not in_table or not col_starts:
            continue

        # Extract columns by position
        parts = []
        for i, start in enumerate(col_starts):
            end = col_starts[i + 1] if i + 1 < len(col_starts) else len(line)
            parts.append(line[start:end].strip())
        
        if len(parts) < 6:
            continue

        kind = parts[0]
        key = parts[1]
        age = parts[2]
        model = parts[3] if len(parts) > 3 else ""
        runtime = parts[4] if len(parts) > 4 else ""
        tokens = parts[5] if len(parts) > 5 else ""
        flags = parts[6] if len(parts) > 6 else ""

        # Extract channel/surface from key
        surface = "unknown"
        channel = ""
        if "disco" in key:  # handles truncated "discord"
            surface = "discord"
            m = re.search(r'disco[^.]*\.\.\.(\d+)', key)
            if m:
                channel = m.group(1)
        elif "teleg" in key:  # handles truncated "telegram"
            surface = "telegram"
        elif "cron" in key:
            surface = "cron"
        elif "subag" in key:  # handles truncated "subagent"
            surface = "subagent"
        elif "heartbeat" in key:
            surface = "heartbeat"
        elif kind == "direct" and "main" in key:
            surface = "direct"
        elif kind == "group":
            surface = "group"

        # Parse tokens: "23k/200k (12%)" or "unknown/200k (?%)"
        token_used = 0
        token_limit = 0
        token_pct = 0
        m = re.search(r'(\d+)k/(\d+)k\s*\((\d+)%\)', tokens)
        if m:
            token_used = int(m.group(1)) * 1000
            token_limit = int(m.group(2)) * 1000
            token_pct = int(m.group(3))
        else:
            # Try "unknown/200k"
            m = re.search(r'unknown/(\d+)k', tokens)
            if m:
                token_limit = int(m.group(1)) * 1000

        # Parse age: "13m ago", "1h ago", "just now", "<1m ago"
        age_seconds = 0
        if "just now" in age or "<1m" in age:
            age_seconds = 0
        else:
            m = re.search(r'(\d+)([smhd])', age)
            if m:
                val = int(m.group(1))
                unit = m.group(2)
                multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                age_seconds = val * multipliers.get(unit, 60)

        # Status
        status = "active" if age_seconds < 3600 else "idle"
        if "aborted" in flags.lower():
            status = "aborted"
        elif "heartbeat" in key.lower():
            status = "heartbeat"

        sessions.append({
            "key": key,
            "kind": kind,
            "age": age,
            "age_seconds": age_seconds,
            "model": model,
            "surface": surface,
            "channel": channel,
            "runtime": runtime,
            "tokens_used": token_used,
            "token_limit": token_limit,
            "token_pct": token_pct,
            "flags": flags,
            "status": status,
        })

    return sessions


def _parse_cron_list(raw):
    """Parse `openclaw cron list` output into structured data."""
    jobs = []
    if not raw:
        return jobs

    lines = raw.split("\n")
    in_table = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("ID") and "Name" in line:
            in_table = True
            continue
        if not in_table:
            continue

        # Format: UUID  name  schedule  next  last  status  target  delivery  agent  model
        # This is tricky to parse because fields can have spaces
        # Strategy: split by UUID pattern first
        parts = line.split(None, 9)
        if len(parts) < 5:
            continue

        job_id = parts[0]
        # The name could be multi-word, so we need to find where the schedule starts
        # Simple heuristic: find fields that look like schedules or timestamps
        name_parts = []
        schedule = ""
        next_run = ""
        last_run = ""
        status = ""
        target = ""
        delivery = ""
        agent = ""
        model = ""

        # Try splitting: ID name... schedule next last status target delivery agent model
        # Schedule patterns: "every Nm", "cron * * * * * *"
        # Next/Last patterns: "in Nm", "Nh ago", "Nd ago", "<1m ago", "never"

        remaining = parts[1:]
        # Find the schedule field (starts with 'every' or 'cron' or 'interval')
        sched_idx = None
        for i, p in enumerate(remaining):
            if p in ("every", "cron", "interval", "at"):
                sched_idx = i
                break

        if sched_idx is not None:
            name_parts = remaining[:sched_idx]
            after_name = remaining[sched_idx:]

            # Schedule + next + last + status
            schedule = " ".join(after_name[:3]) if len(after_name) > 0 else ""
            next_run = after_name[3] if len(after_name) > 3 else ""
            last_run = after_name[4] if len(after_name) > 4 else ""
            status = after_name[5] if len(after_name) > 5 else ""
            target = after_name[6] if len(after_name) > 6 else ""
            delivery = after_name[7] if len(after_name) > 7 else ""
            agent = after_name[8] if len(after_name) > 8 else ""
            model = after_name[9] if len(after_name) > 9 else ""

        jobs.append({
            "id": job_id,
            "name": " ".join(name_parts) if name_parts else job_id[:8],
            "schedule": schedule,
            "next_run": next_run,
            "last_run": last_run,
            "last_status": status,
            "target": target,
            "delivery": delivery,
            "agent": agent,
            "model": model,
        })

    return jobs


def _parse_status(raw):
    """Parse `openclaw status --json` output."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def fetch_all(state: GatewayState):
    """Fetch all data from openclaw CLI and update state."""
    try:
        # Sessions
        sessions_raw = _run_cli(["sessions"], timeout=15)
        if sessions_raw:
            sessions = _parse_sessions(sessions_raw)
            state.update(sessions=sessions, connected=True)

        # Cron jobs
        cron_raw = _run_cli(["cron", "list"], timeout=10)
        if cron_raw:
            cron_jobs = _parse_cron_list(cron_raw)
            state.update(cron_jobs=cron_jobs)

        # Status
        status_raw = _run_cli(["status", "--json"], timeout=10)
        if status_raw:
            status_data = _parse_status(status_raw)
            state.update(
                health={
                    "status": "ok",
                    "version": status_data.get("version"),
                    "uptime": status_data.get("uptime"),
                },
                channels=status_data.get("channels", {}),
                usage=status_data.get("usage", {}),
            )

        # Gateway health (simple HTTP check)
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:18789/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                h = json.loads(resp.read())
                state.update(health={**state.health, "gateway_ok": h.get("ok", False)})
        except Exception:
            pass

    except Exception as e:
        logger.error(f"fetch_all error: {e}")
        state.update(connected=False, error=str(e))


# ── Background poller ─────────────────────────────────────────

class GatewayPoller:
    """Periodically polls openclaw CLI for state updates."""

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
        # Do an immediate fetch
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

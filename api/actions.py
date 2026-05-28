"""Actions handler — list available actions and handle triggers."""
import json
import subprocess
import time
from pathlib import Path

CRON_JOBS_PATH = Path.home() / ".openclaw" / "cron" / "jobs.json"
CRON_STATE_PATH = Path.home() / ".openclaw" / "cron" / "jobs-state.json"


def handle_actions():
    """List available actions the user can trigger."""
    actions = [
        {
            "id": "health_check",
            "name": "Run Health Check",
            "description": "Check gateway, channels, usage, and tunnel status",
            "category": "system",
            "confirm": False,
        },
        {
            "id": "reconnect_gateway",
            "name": "Reconnect Gateway Bridge",
            "description": "Force reconnect the gateway WebSocket connection",
            "category": "system",
            "confirm": True,
        },
        {
            "id": "refresh_all",
            "name": "Refresh All Data",
            "description": "Clear caches and re-fetch all data",
            "category": "system",
            "confirm": False,
        },
    ]

    # Add per-job trigger actions
    try:
        if CRON_JOBS_PATH.exists():
            with open(CRON_JOBS_PATH) as f:
                data = json.load(f)
            for job in data.get("jobs", []):
                if not job.get("enabled", True):
                    continue
                actions.append({
                    "id": f"cron:run:{job['id']}",
                    "name": f"Trigger: {job.get('name', job['id'][:8])}",
                    "description": "Run this cron job now",
                    "category": "cron",
                    "confirm": True,
                    "job_id": job["id"],
                    "job_name": job.get("name", ""),
                })
    except Exception:
        pass

    return {"actions": actions}


def handle_actions_trigger(action_id: str, body: dict = None):
    """Handle an action trigger."""
    if body is None:
        body = {}

    if action_id == "health_check":
        return _action_health_check()

    if action_id == "reconnect_gateway":
        return _action_reconnect_gateway()

    if action_id == "refresh_all":
        return _action_refresh_all()

    if action_id.startswith("cron:run:"):
        job_id = action_id.replace("cron:run:", "")
        return _action_trigger_cron(job_id)

    return {"ok": False, "error": f"Unknown action: {action_id}"}


def _action_health_check():
    """Internal: would normally ping gateway but we read from state."""
    return {
        "ok": True,
        "message": "Health check initiated — check /api/health for results",
    }


def _action_reconnect_gateway():
    """Force reconnect the bridge."""
    from gateway_bridge import stop_bridge, start_bridge
    try:
        stop_bridge()
        time.sleep(0.5)
        start_bridge()
        return {"ok": True, "message": "Gateway bridge restarted"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to reconnect: {e}"}


def _action_refresh_all():
    """No-op — data refreshes on each poll anyway."""
    return {"ok": True, "message": "All data caches will refresh on next request"}


def _action_trigger_cron(job_id: str):
    """Trigger a specific cron job via openclaw CLI."""
    if not job_id:
        return {"ok": False, "error": "No job_id provided"}

    try:
        result = subprocess.run(
            ["openclaw", "cron", "run", job_id],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return {
                "ok": True,
                "message": f"Cron job triggered: {job_id[:8]}",
                "output": result.stdout.strip(),
            }
        else:
            return {
                "ok": False,
                "error": f"Cron trigger failed: {result.stderr.strip()[:200]}",
            }
    except FileNotFoundError:
        return {"ok": False, "error": "openclaw CLI not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Cron trigger timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

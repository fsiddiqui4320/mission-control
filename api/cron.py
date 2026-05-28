"""Cron handler — load cron jobs from gateway config + show last run status."""
import json
import time
from pathlib import Path
from datetime import datetime, timezone


CRON_JOBS_PATH = Path.home() / ".openclaw" / "cron" / "jobs.json"
CRON_STATE_PATH = Path.home() / ".openclaw" / "cron" / "jobs-state.json"


def handle_cron():
    """Return cron jobs with their last run status."""
    jobs = []
    job_states = {}

    # Load state
    try:
        if CRON_STATE_PATH.exists():
            with open(CRON_STATE_PATH) as f:
                state_data = json.load(f)
            job_states = state_data.get("jobs", {})
    except Exception:
        pass

    # Load jobs
    try:
        if CRON_JOBS_PATH.exists():
            with open(CRON_JOBS_PATH) as f:
                jobs_data = json.load(f)
            raw_jobs = jobs_data.get("jobs", [])
    except Exception:
        return {"jobs": [], "note": "No cron config found"}

    now_ms = int(time.time() * 1000)

    for j in raw_jobs:
        job_id = j.get("id", "")
        name = j.get("name", j.get("description", job_id[:8]))
        enabled = j.get("enabled", True)
        schedule = j.get("schedule", {})
        delivery = j.get("delivery", {})

        # Human-readable schedule
        schedule_kind = schedule.get("kind", "cron")
        if schedule_kind == "cron":
            expr = schedule.get("expr", "")
            schedule_text = _cron_to_human(expr)
        elif schedule_kind == "every":
            every_ms = schedule.get("everyMs", 0)
            if every_ms >= 3600000:
                schedule_text = f"Every {every_ms // 3600000}h"
            elif every_ms >= 60000:
                schedule_text = f"Every {every_ms // 60000}m"
            else:
                schedule_text = f"Every {every_ms // 1000}s"
        else:
            schedule_text = schedule_kind

        # State
        state = job_states.get(job_id, {}).get("state", {})
        last_run_ms = state.get("lastRunAtMs")
        next_run_ms = state.get("nextRunAtMs")
        last_run_status = state.get("lastRunStatus", state.get("lastStatus", "unknown"))
        last_duration_ms = state.get("lastDurationMs")
        last_error = state.get("lastError", "")
        consecutive_errors = state.get("consecutiveErrors", 0)
        last_delivered = state.get("lastDelivered", state.get("lastDeliveryStatus") == "delivered")

        # Delivery info
        delivery_mode = delivery.get("mode", "none")
        delivery_channel = delivery.get("channel", "")
        delivery_to = delivery.get("to", "")

        # Status indicator
        if not enabled:
            status = "disabled"
        elif last_run_status == "ok" and not _is_overdue(next_run_ms, now_ms):
            status = "ok"
        elif last_run_status == "error" and not _is_overdue(next_run_ms, now_ms):
            status = "error_recent"
        elif last_run_status == "error" or consecutive_errors > 0:
            status = "error"
        elif _is_overdue(next_run_ms, now_ms):
            status = "overdue"
        elif last_run_ms is None:
            status = "never_run"
        else:
            status = last_run_status

        jobs.append({
            "id": job_id,
            "name": name,
            "enabled": enabled,
            "schedule": schedule_text,
            "schedule_raw": schedule,
            "last_run": datetime.fromtimestamp(last_run_ms / 1000, tz=timezone.utc).isoformat() if last_run_ms else None,
            "next_run": datetime.fromtimestamp(next_run_ms / 1000, tz=timezone.utc).isoformat() if next_run_ms else None,
            "last_status": status,
            "last_duration_ms": last_duration_ms,
            "last_error": last_error,
            "consecutive_errors": consecutive_errors,
            "delivery_channel": delivery_channel,
            "delivery_to": delivery_to,
        })

    # Summary
    summary = {
        "total": len(jobs),
        "enabled": sum(1 for j in jobs if j["enabled"]),
        "ok": sum(1 for j in jobs if j["last_status"] == "ok"),
        "error": sum(1 for j in jobs if j["last_status"] in ("error", "error_recent")),
        "overdue": sum(1 for j in jobs if j["last_status"] == "overdue"),
        "failed_jobs": [j["name"] for j in jobs if j["last_status"] in ("error", "error_recent")],
    }

    return {"jobs": jobs, "summary": summary}


def _cron_to_human(expr: str) -> str:
    """Convert a cron expression to a human-readable description."""
    if not expr:
        return ""
    parts = expr.strip().split()
    if len(parts) < 5:
        return expr

    minute, hour, dom, month, dow = parts[:5]

    # Simple patterns
    if minute == "0" and hour == "9" and dow == "*":
        if dom == "*" and month == "*":
            return "Daily 9am"
    if minute == "0" and hour == "8" and dow == "1-5":
        return "Weekdays 8am"
    if minute == "0" and hour == "9" and dow == "1":
        return "Weekly Mon 9am"
    if minute == "0" and hour == "9" and dow == "2,4":
        return "Tue & Thu 9am"
    if minute == "0" and hour == "20":
        return "Daily 8pm"
    if minute in ("0", "0,30") and hour == "*":
        return "Every 30min"

    return expr


def _is_overdue(next_run_ms, now_ms):
    """Check if a job is overdue."""
    if not next_run_ms:
        return False
    return next_run_ms < (now_ms - 60000)  # 1 minute grace period

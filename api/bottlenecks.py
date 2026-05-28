"""Bottlenecks handler — extract blockers, deadlines, stale projects, failed jobs."""
import json
import time
import re
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path.home() / ".openclaw" / "workspace"
MEMORY_MD = WORKSPACE / "MEMORY.md"
PROJECTS_DIR = WORKSPACE / "projects"
CRON_STATE_PATH = Path.home() / ".openclaw" / "cron" / "jobs-state.json"


def handle_bottlenecks():
    """Return blockers, deadlines, stale projects, and failed cron jobs."""
    blockers = _extract_blockers()
    deadlines = _extract_deadlines()
    stale_projects = _find_stale_projects()
    failed_cron = _find_failed_cron()

    total_issues = (len(blockers) + len(deadlines) + len(stale_projects) +
                    len(failed_cron))

    return {
        "blockers": blockers,
        "deadlines": deadlines,
        "stale_projects": stale_projects,
        "failed_cron": failed_cron,
        "total_issues": total_issues,
    }


def _extract_blockers():
    """Extract persistent blockers from MEMORY.md."""
    blockers = []
    if not MEMORY_MD.exists():
        return blockers

    try:
        content = MEMORY_MD.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return blockers

    # Find the "Persistent Blockers" section
    in_blockers = False
    current_blocker = None

    for line in content.split("\n"):
        stripped = line.strip()

        if "Persistent Blockers" in stripped or "persistent blockers" in stripped.lower():
            in_blockers = True
            continue
        if in_blockers and stripped.startswith("##"):
            break  # Next section

        if in_blockers and stripped:
            # Numbered items like "1. **Study abroad decision** — ..."
            match = re.match(r'\d+\.\s+\*\*(.+?)\*\*\s*[—\-]\s*(.+)', stripped)
            if match:
                blocker_name = match.group(1).strip()
                description = match.group(2).strip()
                # Try to extract deadline
                deadline_match = re.search(r'(?:Deadline|due)\s+(.+?)(?:\s*$|\s*\.)', description, re.IGNORECASE)
                deadline_hint = deadline_match.group(1) if deadline_match else None

                blockers.append({
                    "name": blocker_name,
                    "description": description,
                    "deadline_hint": deadline_hint,
                    "severity": _assess_severity(blocker_name, description),
                    "source": "MEMORY.md",
                })

    return blockers


def _extract_deadlines():
    """Extract upcoming deadlines from MEMORY.md and area files."""
    deadlines = []

    # Known deadlines
    deadlines.append({
        "name": "Study Abroad Decision",
        "description": "Morocco (CIEE Rabat) vs Singapore (NUS/NTU)",
        "deadline": "Early June 2026 (~1 week)",
        "severity": "critical",
        "source": "MEMORY.md",
    })

    # Check for resume deadline
    try:
        if MEMORY_MD.exists():
            content = MEMORY_MD.read_text(encoding="utf-8", errors="ignore")
            # Look for date patterns near "deadline" or "due"
            for line in content.split("\n"):
                if "deadline" in line.lower() or "due" in line.lower():
                    if re.search(r'(?:june|july|aug|2026)', line, re.IGNORECASE):
                        deadlines.append({
                            "name": "Deadline mentioned",
                            "description": line.strip()[:200],
                            "severity": "warning",
                            "source": "MEMORY.md",
                        })
    except Exception:
        pass

    return deadlines


def _find_stale_projects():
    """Find projects with no activity in 14+ days."""
    stale = []
    now = time.time()

    if not PROJECTS_DIR.exists():
        return stale

    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        try:
            mtime = d.stat().st_mtime
        except OSError:
            continue

        age_days = (now - mtime) / 86400
        if age_days >= 14:
            stale.append({
                "name": d.name,
                "age_days": round(age_days, 1),
                "severity": "warning" if age_days < 30 else "info",
                "last_modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            })

    stale.sort(key=lambda x: x["age_days"], reverse=True)
    return stale


def _find_failed_cron():
    """Find cron jobs that errored on last run."""
    failed = []
    try:
        if CRON_STATE_PATH.exists():
            with open(CRON_STATE_PATH) as f:
                data = json.load(f)
            for job_id, job_data in data.get("jobs", {}).items():
                state = job_data.get("state", {})
                status = state.get("lastRunStatus", state.get("lastStatus", "unknown"))
                if status == "error":
                    consecutive = state.get("consecutiveErrors", 0)
                    error_msg = state.get("lastError", "Unknown error")
                    failed.append({
                        "job_id": job_id,
                        "error": error_msg,
                        "consecutive_errors": consecutive,
                        "severity": "critical" if consecutive >= 3 else "warning",
                        "last_run": datetime.fromtimestamp(
                            state.get("lastRunAtMs", 0) / 1000, tz=timezone.utc
                        ).isoformat() if state.get("lastRunAtMs") else None,
                    })
    except Exception:
        pass
    return failed


def _assess_severity(name: str, description: str) -> str:
    """Assess blocker severity based on keywords."""
    text = (name + " " + description).lower()
    if any(w in text for w in ("deadline", "urgent", "asap", "critical", "blocking")):
        return "critical"
    if any(w in text for w in ("important", "need", "must", "required")):
        return "warning"
    return "info"

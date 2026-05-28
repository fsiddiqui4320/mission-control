"""Pulse handler — active sessions, recent activity, agent status."""
import os
import time
from pathlib import Path
from datetime import datetime, timezone

from gateway_bridge import get_state

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))


def handle_pulse():
    """Return live session and activity data from CLI bridge."""
    state = get_state()
    snapshot = state.snapshot()

    # Map CLI session format to frontend-friendly format
    active_sessions = []
    for s in snapshot.get("sessions", []):
        if not isinstance(s, dict):
            continue
        active_sessions.append({
            "key": s.get("key", ""),
            "kind": s.get("kind", ""),
            "surface": s.get("surface", "unknown"),
            "channel": s.get("channel", ""),
            "model": s.get("model", ""),
            "age": s.get("age", ""),
            "age_seconds": s.get("age_seconds", 0),
            "runtime": s.get("runtime", ""),
            "tokens_used": s.get("tokens_used", 0),
            "token_limit": s.get("token_limit", 0),
            "token_pct": s.get("token_pct", 0),
            "flags": s.get("flags", ""),
            "status": s.get("status", "idle"),
        })

    # Recent file activity
    recent_files = _get_recent_files(24)

    # Agent status from session activity
    agent_status = _get_agent_status(active_sessions)

    # Quick stats summary
    quick_stats = {
        "active_session_count": len(active_sessions),
        "recent_file_changes": len(recent_files),
        "gateway_connected": snapshot.get("connected", False),
        "total_tokens_used": sum(s.get("tokens_used", 0) for s in active_sessions),
        "surfaces": list(set(s.get("surface") for s in active_sessions)),
    }

    return {
        "active_sessions": active_sessions,
        "recent_activity": recent_files[:10],
        "agent_status": agent_status,
        "quick_stats": quick_stats,
    }


def _get_agent_status(sessions):
    """Compute agent status summary from sessions."""
    if not sessions:
        return {"status": "idle", "label": "Idle", "active_count": 0}

    active = [s for s in sessions if s.get("status") == "active"]
    systems = [s for s in sessions if s.get("status") == "system"]
    aborted = [s for s in sessions if s.get("status") == "aborted"]

    if active:
        return {
            "status": "active",
            "label": f"Active ({len(active)} sessions)",
            "active_count": len(active),
        }
    if systems:
        return {
            "status": "system",
            "label": f"System ({len(systems)} jobs)",
            "active_count": len(systems),
        }
    return {"status": "idle", "label": "Idle", "active_count": 0}


def _get_recent_files(hours: int = 24):
    """Get files modified recently in the workspace."""
    cutoff = time.time() - (hours * 3600)
    results = []
    try:
        for root, dirs, files in os.walk(WORKSPACE):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                        {'node_modules', '__pycache__', '.git', '.vercel', 'dist', 'build', '.next'}]
            for fname in files:
                if fname.startswith('.'):
                    continue
                fpath = Path(root) / fname
                try:
                    stat = fpath.stat()
                    if stat.st_mtime < cutoff:
                        continue
                    rel = fpath.relative_to(WORKSPACE)
                    results.append({
                        "path": str(rel),
                        "name": fname,
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "type": fpath.suffix.lstrip(".") or "file",
                        "size": stat.st_size,
                    })
                except OSError:
                    pass
    except PermissionError:
        pass
    results.sort(key=lambda x: x["modified"], reverse=True)
    return results[:20]

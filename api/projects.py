"""Projects handler — scan workspace projects with staleness indicators."""
import os
import re
import time
from pathlib import Path
from datetime import datetime, timezone


WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
PROJECTS_DIR = WORKSPACE / "projects"

SKIP_DIRS = {'.git', '.vercel', 'node_modules', '__pycache__', '.DS_Store', '.next', 'dist', 'build'}
SKIP_FILE_EXTENSIONS = {'.pyc', '.pyo', '.map', '.lock', '.bin'}


def safe_walk(directory: Path):
    """Walk directory tree, skipping noise."""
    try:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith('.') or entry.name in SKIP_DIRS:
                continue
            if entry.is_dir():
                yield from safe_walk(entry)
            elif entry.is_file() and entry.suffix not in SKIP_FILE_EXTENSIONS:
                yield entry
    except PermissionError:
        pass


def safe_md_walk(directory: Path):
    """Walk directory tree for .md files only."""
    try:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith('.') or entry.name in SKIP_DIRS:
                continue
            if entry.is_dir():
                yield from safe_md_walk(entry)
            elif entry.is_file() and entry.suffix == '.md':
                yield entry
    except PermissionError:
        pass


def _count_tasks_in_dir(d: Path) -> int:
    """Count checklist and TODO tasks in markdown files."""
    count = 0
    for f in safe_md_walk(d):
        try:
            for line in f.read_text(encoding="utf-8", errors="ignore").split("\n"):
                stripped = line.strip()
                if re.search(r'-\s*\[[xX >/~]\]', stripped):
                    count += 1
                elif re.search(r'\bTODO\b|\bFIXME\b', stripped):
                    count += 1
        except Exception:
            pass
    return count


def _get_git_status(d: Path) -> str:
    """Get git status for a directory if it's a git repo."""
    git_dir = d / ".git"
    if not git_dir.exists():
        return "no-repo"

    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(d), "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return "error"
        if not result.stdout.strip():
            # Check if there are unpushed commits
            result2 = subprocess.run(
                ["git", "-C", str(d), "log", "--oneline", "@{u}..HEAD"],
                capture_output=True, text=True, timeout=5
            )
            if result2.returncode == 0 and result2.stdout.strip():
                return "unpushed"
            return "clean"
        return "dirty"
    except Exception:
        return "unknown"


def handle_projects():
    """Return project list with activity indicators."""
    projects = []
    now = time.time()
    now_dt = datetime.now(timezone.utc)

    if not PROJECTS_DIR.exists():
        return {"projects": [], "note": "No projects directory found"}

    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue

        spec = d / "SPEC.md"
        try:
            mtime = d.stat().st_mtime
        except OSError:
            mtime = 0

        files = list(safe_walk(d))
        tasks = _count_tasks_in_dir(d)
        git_status = _get_git_status(d)

        age_hours = (now - mtime) / 3600 if mtime > 0 else 999
        is_active = age_hours <= 24
        is_stale = age_hours >= (7 * 24)
        is_dead = age_hours >= (14 * 24)

        # Get most recent file changes
        recent_changes = []
        for f in safe_walk(d):
            try:
                fmtime = f.stat().st_mtime
                if fmtime >= (now - 5 * 24 * 3600):  # within 5 days
                    recent_changes.append({
                        "name": f.name,
                        "modified": datetime.fromtimestamp(fmtime, tz=timezone.utc).isoformat(),
                    })
            except OSError:
                pass
        recent_changes.sort(key=lambda x: x["modified"], reverse=True)
        recent_changes = recent_changes[:5]

        projects.append({
            "name": d.name,
            "path": str(d),
            "has_spec": spec.exists(),
            "file_count": len(files),
            "task_count": tasks,
            "modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat() if mtime > 0 else None,
            "git_status": git_status,
            "is_active": is_active,
            "is_stale": is_stale,
            "is_dead": is_dead,
            "age_hours": round(age_hours, 1),
            "recent_changes": recent_changes,
        })

    # Sort: active first, then by name
    projects.sort(key=lambda p: (not p.get("is_active", False), p["name"]))

    summary = {
        "total": len(projects),
        "active": sum(1 for p in projects if p.get("is_active")),
        "stale": sum(1 for p in projects if p.get("is_stale") and not p.get("is_active")),
        "dead": sum(1 for p in projects if p.get("is_dead")),
    }

    return {"projects": projects, "summary": summary}

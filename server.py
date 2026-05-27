#!/usr/bin/env python3
"""Mission Control - lightweight API server for the OpenClaw dashboard."""
import json
import os
import re
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import datetime

WORKSPACE    = Path(os.path.expanduser("~/.openclaw/workspace"))
PROJECTS_DIR = WORKSPACE / "projects"
MEMORY_DIR   = WORKSPACE / "memory"

# Skip hidden dirs and common noise
SKIP_DIRS = {'.git', '.vercel', 'node_modules', '__pycache__', '.DS_Store', '.next', 'dist', 'build'}
SKIP_FILE_EXTENSIONS = {'.pyc', '.pyo', '.map', '.lock', '.bin'}


def safe_walk(directory: Path):
    """Walk directory tree, skipping noise dirs at traversal level."""
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
    """Walk directory tree for .md files only, skipping noise dirs."""
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


class APIHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        route  = parsed.path

        routes = {
            "/api/status":   self._status,
            "/api/projects": self._projects,
            "/api/memories": self._memories,
            "/api/docs":     self._docs,
            "/api/tasks":    self._tasks,
            "/api/cron":     self._cron,
            "/api/activity": self._activity,
            "/api/team":     self._team,
        }

        handler = routes.get(route)
        if handler:
            self._json(handler())
            return

        if self.path in ("/", ""):
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, fmt, *args):
        # Suppress static file noise; only log API calls
        if '/api/' in args[0] if args else False:
            super().log_message(fmt, *args)

    def _json(self, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # ── Route handlers ────────────────────────────────────────

    def _status(self):
        return {
            "status":    "ok",
            "workspace": str(WORKSPACE),
            "exists":    WORKSPACE.exists(),
        }

    def _projects(self):
        projects = []
        if not PROJECTS_DIR.exists():
            return projects
        for d in sorted(PROJECTS_DIR.iterdir()):
            if not d.is_dir() or d.name.startswith('.'):
                continue
            spec   = d / "SPEC.md"
            files  = list(safe_walk(d))
            tasks  = self._count_tasks_in_dir(d)
            mtime  = d.stat().st_mtime
            projects.append({
                "name":       d.name,
                "path":       str(d),
                "has_spec":   spec.exists(),
                "file_count": len(files),
                "task_count": tasks,
                "modified":   datetime.datetime.fromtimestamp(mtime).isoformat(),
            })
        return projects

    def _memories(self):
        memories = {"daily": [], "areas": [], "resources": [], "other": []}
        if not MEMORY_DIR.exists():
            return memories
        for f in safe_md_walk(MEMORY_DIR):
            rel   = str(f.relative_to(MEMORY_DIR))
            entry = {
                "name":     f.stem,
                "path":     str(f),
                "relative": rel,
                "size":     f.stat().st_size,
                "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            if rel.startswith("areas/"):
                memories["areas"].append(entry)
            elif rel.startswith("resources/"):
                memories["resources"].append(entry)
            elif re.match(r"^\d{4}", rel):  # YYYY-… files
                memories["daily"].append(entry)
            else:
                memories["other"].append(entry)
        return memories

    def _docs(self):
        docs = []
        if not WORKSPACE.exists():
            return docs
        for f in safe_md_walk(WORKSPACE):
            rel = str(f.relative_to(WORKSPACE))
            # Exclude memory and project internal files
            if rel.startswith("memory/") or "/memory/" in rel:
                continue
            docs.append({
                "name":     f.stem,
                "path":     rel,
                "size":     f.stat().st_size,
                "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        return docs

    def _tasks(self):
        tasks = []
        if not WORKSPACE.exists():
            return tasks
        for f in safe_md_walk(WORKSPACE):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n"):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    status = self._task_status(stripped)
                    if status:
                        tasks.append({
                            "title":  stripped,
                            "source": str(f.relative_to(WORKSPACE)),
                            "status": status,
                        })
            except Exception:
                pass
        # Sort: in_progress first, then todo, then done
        order = {"in_progress": 0, "todo": 1, "done": 2}
        tasks.sort(key=lambda t: order.get(t["status"], 99))
        return tasks[:80]

    def _cron(self):
        """Try to load cron configuration from known openclaw paths."""
        candidates = [
            Path.home() / ".openclaw" / "crons.json",
            Path.home() / ".openclaw" / "config" / "crons.json",
            WORKSPACE / "crons.json",
            WORKSPACE / "config" / "crons.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    return json.loads(path.read_text())
                except Exception:
                    pass
        return {"jobs": [], "note": "No cron config found"}

    def _activity(self):
        """Return recently modified files, newest first."""
        if not WORKSPACE.exists():
            return []
        cutoff  = datetime.datetime.now() - datetime.timedelta(days=14)
        results = []
        for f in safe_walk(WORKSPACE):
            try:
                mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    continue
                results.append({
                    "path":     str(f.relative_to(WORKSPACE)),
                    "name":     f.name,
                    "modified": mtime.isoformat(),
                    "type":     f.suffix.lstrip(".") or "file",
                })
            except Exception:
                pass
        results.sort(key=lambda x: x["modified"], reverse=True)
        return results[:40]

    def _team(self):
        """Return agent roster from config if available."""
        candidates = [
            Path.home() / ".openclaw" / "agents.json",
            Path.home() / ".openclaw" / "config" / "agents.json",
            WORKSPACE / "agents.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "agents" in data:
                        return data["agents"]
                except Exception:
                    pass
        return []  # JS falls back to defaults

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _skip(path: Path) -> bool:
        return any(part in SKIP_DIRS or part.startswith('.') for part in path.parts)

    @staticmethod
    def _task_status(line: str):
        lower = line.lower()
        # Completed: - [x] or - [X]
        if re.search(r'-\s*\[[xX]\]', line):
            return "done"
        # In progress: - [>] or - [/] or - [~]
        if re.search(r'-\s*\[[>/~]\]', line):
            return "in_progress"
        # Open: - [ ]
        if re.search(r'-\s*\[\s\]', line):
            return "todo"
        # TODO / FIXME markers (not inside done items)
        if re.search(r'\bTODO\b|\bFIXME\b', line):
            return "todo"
        return None

    def _count_tasks_in_dir(self, d: Path) -> int:
        count = 0
        for f in safe_md_walk(d):
            try:
                for line in f.read_text(encoding="utf-8", errors="ignore").split("\n"):
                    if self._task_status(line.strip()):
                        count += 1
            except Exception:
                pass
        return count


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"🚀 Mission Control on http://localhost:{port}")
    print(f"   Workspace: {WORKSPACE}")
    HTTPServer(("127.0.0.1", port), APIHandler).serve_forever()

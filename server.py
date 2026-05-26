#!/usr/bin/env python3
"""Mission Control - lightweight API server for the OpenClaw dashboard."""
import json
import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import subprocess
import datetime

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
PROJECTS_DIR = WORKSPACE / "projects"
MEMORY_DIR = WORKSPACE / "memory"

class APIHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        # API routes
        if parsed.path == "/api/status":
            self._json({"status": "ok", "workspace": str(WORKSPACE)})
            return
        
        if parsed.path == "/api/projects":
            self._json(self._list_projects())
            return
        
        if parsed.path == "/api/memories":
            self._json(self._list_memories())
            return
        
        if parsed.path == "/api/docs":
            self._json(self._list_docs())
            return
        
        if parsed.path == "/api/tasks":
            self._json(self._list_tasks())
            return
        
        if parsed.path == "/api/cron":
            self._json(self._list_cron())
            return
            
        # Serve static files
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)
    
    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
    def _list_projects(self):
        projects = []
        if PROJECTS_DIR.exists():
            for d in sorted(PROJECTS_DIR.iterdir()):
                if d.is_dir() and not d.name.startswith('.'):
                    spec = d / "SPEC.md"
                    projects.append({
                        "name": d.name,
                        "path": str(d),
                        "has_spec": spec.exists(),
                        "modified": datetime.datetime.fromtimestamp(d.stat().st_mtime).isoformat()
                    })
        return projects
    
    def _list_memories(self):
        memories = {"daily": [], "areas": [], "resources": [], "other": []}
        if MEMORY_DIR.exists():
            for f in sorted(MEMORY_DIR.rglob("*.md")):
                rel = str(f.relative_to(MEMORY_DIR))
                entry = {
                    "name": f.stem,
                    "path": str(f),
                    "relative": rel,
                    "size": f.stat().st_size,
                    "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }
                if rel.startswith("areas/"):
                    memories["areas"].append(entry)
                elif rel.startswith("resources/"):
                    memories["resources"].append(entry)
                elif rel.startswith("20"):  # YYYY-MM-DD.md
                    memories["daily"].append(entry)
                else:
                    memories["other"].append(entry)
        return memories
    
    def _list_docs(self):
        docs = []
        for f in sorted(WORKSPACE.rglob("*.md")):
            if '/memory/' not in str(f) and '/projects/' not in str(f):
                docs.append({
                    "name": f.stem,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
        return docs
    
    def _list_tasks(self):
        tasks = []
        # Scan workspace for TODO markers
        for f in WORKSPACE.rglob("*.md"):
            try:
                content = f.read_text()
                for line in content.split('\n'):
                    if '- [ ]' in line or 'TODO' in line or 'FIXME' in line:
                        tasks.append({
                            "title": line.strip(),
                            "source": str(f.relative_to(WORKSPACE)),
                            "status": "todo" if '- [ ]' in line else "pending"
                        })
            except:
                pass
        return tasks[:50]  # limit
    
    def _list_cron(self):
        """Read cron jobs from openclaw config or return placeholder."""
        return {"jobs": [], "note": "Cron integration pending"}

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"🚀 Mission Control starting on http://localhost:{port}")
    HTTPServer(("127.0.0.1", port), APIHandler).serve_forever()

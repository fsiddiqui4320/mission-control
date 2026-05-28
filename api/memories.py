"""Memories handler — list and search memory files."""
import re
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path.home() / ".openclaw" / "workspace"
MEMORY_DIR = WORKSPACE / "memory"

SKIP_DIRS = {'.git', '.vercel', 'node_modules', '__pycache__', '.DS_Store'}
SKIP_FILE_EXTENSIONS = {'.pyc', '.pyo', '.map', '.lock', '.bin'}


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


def handle_memories(query=None):
    """Return memory files organized by category, optionally filtered by search."""
    memories = {"daily": [], "areas": [], "resources": [], "other": []}

    if not MEMORY_DIR.exists():
        return {"memories": memories, "total": 0}

    for f in safe_md_walk(MEMORY_DIR):
        rel = str(f.relative_to(MEMORY_DIR))
        try:
            stat = f.stat()
        except OSError:
            continue

        entry = {
            "name": f.stem,
            "path": str(f),
            "relative": rel,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "preview": _get_preview(f),
        }

        # Search filter
        if query:
            q = query.lower()
            if q not in entry["name"].lower() and q not in entry.get("preview", "").lower():
                continue

        if rel.startswith("areas/"):
            memories["areas"].append(entry)
        elif rel.startswith("resources/"):
            memories["resources"].append(entry)
        elif re.match(r"^\d{4}-\d{2}-\d{2}", rel):
            memories["daily"].append(entry)
        else:
            memories["other"].append(entry)

    # Sort daily by date descending (newest first)
    memories["daily"].sort(key=lambda x: x["relative"], reverse=True)

    return {
        "memories": memories,
        "total": sum(len(v) for v in memories.values()),
    }


def _get_preview(f: Path, lines: int = 2) -> str:
    """Get the first few non-empty, non-heading lines of a file."""
    try:
        content = f.read_text(encoding="utf-8", errors="ignore")
        preview_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                if preview_lines:
                    break
                continue
            if stripped.startswith("#"):
                continue
            preview_lines.append(stripped[:120])
            if len(preview_lines) >= lines:
                break
        return " ".join(preview_lines)
    except Exception:
        return ""

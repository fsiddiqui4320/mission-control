#!/usr/bin/env bash
# sync-workspace.sh
# Scans Octo's workspace and pushes structured data to octo-workspace-data repo.
# Run via cron or manually. Generates JSON the Mission Control API serves.
#
# Usage: ./sync-workspace.sh
# Requires: git access to fsiddiqui4320/octo-workspace-data

set -euo pipefail
WORKSPACE="${OCTO_WORKSPACE:-$HOME/.openclaw/workspace}"
DATA_REPO="$HOME/.openclaw/octo-workspace-data"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# ── Clone/pull data repo ──────────────────────────────────────
if [ ! -d "$DATA_REPO" ]; then
  git clone "https://fsiddiqui4320:${GITHUB_TOKEN}@github.com/fsiddiqui4320/octo-workspace-data.git" "$DATA_REPO"
  cd "$DATA_REPO"
  # Handle empty repo: create initial commit if needed
  if ! git rev-parse HEAD >/dev/null 2>&1; then
    git commit --allow-empty -m "Initial commit"
    git push origin main
  fi
else
  cd "$DATA_REPO" && git pull origin main 2>/dev/null || true
fi

cd "$DATA_REPO"
rm -rf data/
mkdir -p data/memory data/docs

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── Status ────────────────────────────────────────────────────
cat > data/status.json <<JSON
{
  "status": "ok",
  "workspace": "$WORKSPACE",
  "synced_at": "$TIMESTAMP",
  "host": "$(hostname)"
}
JSON

# ── Tasks (scan MEMORY.md + recent daily notes for TODOs) ────
python3 <<'PY' > data/tasks.json
import re, json, os, sys
from pathlib import Path
from datetime import datetime

ws = os.environ.get('OCTO_WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
tasks = []

def scan_file(path, source):
    try:
        text = Path(path).read_text()
    except:
        return
    # Match lines with task markers: - [ ] or TODO or - [x] (done)
    for line in text.split('\n'):
        line = line.strip()
        m = re.match(r'^[-*]\s*\[([ x])\]\s*(.+)', line, re.IGNORECASE)
        if m:
            status = 'done' if m.group(1).lower() == 'x' else 'todo'
            tasks.append({'title': m.group(2).strip(), 'source': source, 'status': status})
        elif re.match(r'^(TODO|FIXME|HACK|XXX)[: ]', line, re.IGNORECASE):
            tasks.append({'title': line, 'source': source, 'status': 'todo'})

# Scan key files
scan_file(os.path.join(ws, 'MEMORY.md'), 'MEMORY.md')
scan_file(os.path.join(ws, 'SOUL.md'), 'SOUL.md')

# Scan recent daily notes
mem_dir = Path(ws) / 'memory'
for f in sorted(mem_dir.glob('2026-*.md'), reverse=True)[:7]:
    scan_file(str(f), f"memory/{f.name}")

# Deduplicate by title
seen = set()
unique = []
for t in tasks:
    key = t['title'][:80]
    if key not in seen:
        seen.add(key)
        unique.append(t)

json.dump(unique, sys.stdout, indent=2)
PY

# ── Projects ──────────────────────────────────────────────────
python3 <<'PY' > data/projects.json
import json, os, sys
from pathlib import Path
from datetime import datetime

ws = os.environ.get('OCTO_WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
proj_dir = Path(ws) / 'projects'
projects = []

if proj_dir.exists():
    for d in sorted(proj_dir.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        try:
            files = list(d.rglob('*'))
            md_files = [f for f in files if f.suffix == '.md']
            spec = any('spec' in f.name.lower() for f in md_files)
            modified_ts = max((f.stat().st_mtime for f in files), default=0)
            projects.append({
                'name': d.name,
                'path': str(d.relative_to(ws)),
                'modified': datetime.fromtimestamp(modified_ts).isoformat(),
                'file_count': len([f for f in files if f.is_file()]),
                'has_spec': spec,
                'task_count': 0
            })
        except:
            pass

json.dump(projects, sys.stdout, indent=2)
PY

# ── Memories ──────────────────────────────────────────────────
python3 <<'PY' > data/memories.json
import json, os, sys
from pathlib import Path
from datetime import datetime

ws = os.environ.get('OCTO_WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
mem_dir = Path(ws) / 'memory'

def scan_dir(d, prefix=''):
    items = []
    if not d.exists():
        return items
    for f in sorted(d.iterdir()):
        if f.name.startswith('.'):
            continue
        if f.is_dir():
            # recurse into areas/, resources/, archive/
            items.extend(scan_dir(f, prefix=f'{prefix}{f.name}/'))
        elif f.suffix == '.md':
            try:
                stat = f.stat()
                items.append({
                    'relative': str(f.relative_to(ws)),
                    'name': f.name if not prefix else f'{prefix}{f.name}',
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except:
                pass
    return items

all_items = scan_dir(mem_dir)

# Categorize
daily = [i for i in all_items if '/areas/' not in i['relative'] and '/resources/' not in i['relative'] and '/archive/' not in i['relative']]
areas = [i for i in all_items if '/areas/' in i['relative']]
resources = [i for i in all_items if '/resources/' in i['relative']]

result = {
    'daily': sorted(daily, key=lambda x: x['relative'], reverse=True)[:14],
    'areas': sorted(areas, key=lambda x: x['relative']),
    'resources': sorted(resources, key=lambda x: x['relative'])
}
json.dump(result, sys.stdout, indent=2)
PY

# ── Documents ─────────────────────────────────────────────────
python3 <<'PY' > data/docs.json
import json, os, sys
from pathlib import Path
from datetime import datetime

ws = os.environ.get('OCTO_WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
docs = []

# Scan workspace root for spec/docs files
for path in ['SPEC.md', 'TOOLS.md', 'AGENTS.md']:
    fp = Path(ws) / path
    if fp.exists():
        stat = fp.stat()
        docs.append({
            'name': fp.stem,
            'path': path,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

# Scan project specs
proj_dir = Path(ws) / 'projects'
if proj_dir.exists():
    for d in sorted(proj_dir.iterdir()):
        if not d.is_dir() or d.name.startswith('.'):
            continue
        for md in sorted(d.glob('*.md')):
            try:
                stat = md.stat()
                docs.append({
                    'name': md.stem,
                    'path': str(md.relative_to(ws)),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except:
                pass

json.dump(docs, sys.stdout, indent=2)
PY

# ── Team ──────────────────────────────────────────────────────
cat > data/team.json <<'JSON'
[
  {
    "name": "Octo Prime",
    "avatar": "🐙",
    "role": "Main orchestration agent",
    "status": "active",
    "model": "deepseek-v4-pro"
  },
  {
    "name": "Claude Code",
    "avatar": "🤖",
    "role": "Dev sub-agent",
    "status": "idle",
    "model": "claude-sonnet-4-6"
  }
]
JSON

# ── Activity feed (from recent daily notes) ──────────────────
python3 <<'PY' > data/activity.json
import json, os, re, sys
from pathlib import Path
from datetime import datetime

ws = os.environ.get('OCTO_WORKSPACE', os.path.expanduser('~/.openclaw/workspace'))
mem_dir = Path(ws) / 'memory'
activity = []

# Extract notable events from daily notes (headings starting with ##)
daily_files = sorted(mem_dir.glob('2026-*.md'), reverse=True)[:5]
for df in daily_files:
    try:
        text = df.read_text()
        date_str = df.stem
        for line in text.split('\n'):
            # Match headings that look like activities
            m = re.match(r'^##\s+(.+)', line)
            if m and not m.group(1).startswith('#') and len(m.group(1)) > 5:
                activity.append({
                    'type': 'md',
                    'name': m.group(1).strip().rstrip('.'),
                    'path': f'memory/{df.name}',
                    'modified': f'{date_str}T12:00:00'
                })
    except:
        pass

json.dump(activity[:20], sys.stdout, indent=2)
PY

# ── Cron/calendar ─────────────────────────────────────────────
cat > data/cron.json <<'JSON'
{
  "jobs": [
    {"name": "Heartbeat check — email + calendar", "schedule": "every 30min", "cron": "0,30 * * * *"},
    {"name": "Memory consolidation (weekly)", "schedule": "weekly Mon 9am", "cron": "0 9 * * 1"},
    {"name": "Daily brief summary", "schedule": "daily 8pm", "cron": "0 20 * * *"},
    {"name": "Study abroad deadline reminder", "schedule": "daily 9am", "cron": "0 9 * * *"}
  ]
}
JSON

# ── Commit and push ───────────────────────────────────────────
git add data/
if git diff --cached --quiet; then
  echo "No changes to sync."
else
  git -c user.name="Octo" -c user.email="octo@withocto.co" commit -m "sync: $(date '+%Y-%m-%d %H:%M')"
  git push origin main
  echo "✅ Synced workspace data ($TIMESTAMP)"
fi

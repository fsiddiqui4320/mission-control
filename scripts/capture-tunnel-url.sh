#!/bin/bash
# Extract tunnel URL from cloudflared logs and push to GitHub
# Run periodically to keep the discovery URL fresh

PROJECT_DIR="/Users/bigclaw/.openclaw/workspace/projects/mission-control"
LOG_FILE="$PROJECT_DIR/logs/tunnel-err.log"
URL_FILE="$PROJECT_DIR/tunnel-url.txt"

# Extract the most recent trycloudflare URL from logs
URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG_FILE" 2>/dev/null | tail -1)

if [ -z "$URL" ]; then
  echo "[capture-url] No tunnel URL found in logs"
  exit 0
fi

# Check if URL changed
if [ -f "$URL_FILE" ] && [ "$(cat "$URL_FILE")" = "$URL" ]; then
  exit 0  # No change, nothing to do
fi

echo "$URL" > "$URL_FILE"
echo "[capture-url] New tunnel URL: $URL"

# Push to GitHub
cd "$PROJECT_DIR"
git add tunnel-url.txt 2>/dev/null
git commit -m "🤖 Update tunnel URL: $URL" 2>/dev/null || true
git push origin main 2>/dev/null && echo "[capture-url] Pushed to GitHub" || echo "[capture-url] Git push failed (non-fatal)"

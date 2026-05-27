#!/bin/bash
# Mission Control — start server + Cloudflare tunnel, persist tunnel URL

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TUNNEL_URL_FILE="$PROJECT_DIR/tunnel-url.txt"
PORT=5555
CLOUDFLARED="/Users/bigclaw/bin/cloudflared"

log() { echo "[mc-tunnel] $(date '+%H:%M:%S') $*"; }

# ── 1. Kill any existing server/tunnel on our port ──
old_server=$(lsof -ti :$PORT 2>/dev/null) || true
old_tunnel=$(pgrep -f "cloudflared.*localhost:${PORT}" 2>/dev/null) || true
if [ -n "$old_server" ]; then kill "$old_server" 2>/dev/null && log "Killed old server PID $old_server" || true; fi
if [ -n "$old_tunnel" ]; then kill "$old_tunnel" 2>/dev/null && log "Killed old tunnel PID $old_tunnel" || true; fi
sleep 1

# ── 2. Start Python server ──
log "Starting Mission Control server on :$PORT"
cd "$PROJECT_DIR"
python3 server.py $PORT &
SERVER_PID=$!
sleep 2

# Verify server is up
for i in 1 2 3 4 5; do
  if curl -sf http://localhost:$PORT/api/status > /dev/null 2>&1; then break; fi
  log "Waiting for server… ($i/5)"
  sleep 2
done
if ! curl -sf http://localhost:$PORT/api/status > /dev/null 2>&1; then
  log "ERROR: Server failed to start"
  exit 1
fi
log "Server running (PID $SERVER_PID)"

# ── 3. Start Cloudflare tunnel ──
log "Starting Cloudflare tunnel for localhost:$PORT"
$CLOUDFLARED tunnel --url "http://localhost:${PORT}" --no-autoupdate 2>&1 | while IFS= read -r line; do
  echo "[mc-tunnel] $line"
  
  # Extract the trycloudflare.com URL
  if [[ "$line" =~ https://[a-z0-9-]+\.trycloudflare\.com ]]; then
    URL="${BASH_REMATCH[0]}"
    log "Tunnel URL: $URL"
    echo "$URL" > "$TUNNEL_URL_FILE"
    
    # Push to GitHub so frontend can discover it
    cd "$PROJECT_DIR"
    if git diff --quiet tunnel-url.txt 2>/dev/null || ! git diff --quiet tunnel-url.txt 2>/dev/null; then
      git add tunnel-url.txt 2>/dev/null
      git commit -m "🤖 Update tunnel URL: $URL" 2>/dev/null || true
      git push origin main 2>/dev/null && log "Pushed tunnel URL to GitHub" || log "Git push failed (non-fatal)"
    fi
  fi
done &

TUNNEL_PID=$!

# ── 4. Wait and keep alive ──
log "All systems go. Waiting… (server=$SERVER_PID tunnel=$TUNNEL_PID)"
wait $SERVER_PID $TUNNEL_PID 2>/dev/null
log "A process exited — restarting in 5s…"
exit 1  # launchd will restart us

#!/bin/bash
exec > /Users/bigclaw/.openclaw/workspace/projects/mission-control/logs/wrapper.log 2>&1
echo "=== Starting $(date) ==="
echo "PATH=$PATH"
echo "HOME=$HOME"
echo "PWD=$PWD"
/usr/bin/python3 /Users/bigclaw/.openclaw/workspace/projects/mission-control/server.py 5555 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"
sleep 3
curl -sf http://localhost:5555/api/status && echo "Server OK" || echo "Server FAILED"
/Users/bigclaw/bin/cloudflared tunnel --url http://localhost:5555 --no-autoupdate &
TUNNEL_PID=$!
echo "Tunnel PID: $TUNNEL_PID"
echo "Waiting..."
wait

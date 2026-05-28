#!/usr/bin/env python3
"""
Mission Control v2 — lightweight API server + Gateway WebSocket bridge.
Serves REST API consumed by the frontend (static HTML on Vercel).
Gateway WS connection runs in a background thread; handlers read shared state.
"""
import json
import os
import time
import signal
import logging
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

import gateway_bridge
from api import (
    handle_pulse, handle_projects, handle_cron,
    handle_health, handle_memories, handle_bottlenecks,
    handle_actions, handle_actions_trigger,
)

# ── Logging ────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("server")

# ── Config ─────────────────────────────────────────────────────

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace"))
SERVER_DIR = Path(__file__).resolve().parent
START_TIME = time.time()


# ── JSON helper ────────────────────────────────────────────────

def make_response(data, source="filesystem"):
    """Wrap data in standard response envelope."""
    return {
        "ok": True,
        "data": data,
        "meta": {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "uptime_seconds": round(time.time() - START_TIME),
        },
    }


def make_error(message, source="error"):
    """Return a standardized error response."""
    return {
        "ok": False,
        "error": message,
        "meta": {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "uptime_seconds": round(time.time() - START_TIME),
        },
    }


# ── API Handler ────────────────────────────────────────────────

class APIHandler(SimpleHTTPRequestHandler):
    """HTTP handler for Mission Control API and static files."""

    def __init__(self, *args, **kwargs):
        # Set serving directory to project root for static files
        self.directory = str(SERVER_DIR)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)

        # ── API routes ──
        if route == "/api/status":
            self._json_ok(self._status())
            return

        if route == "/api/pulse":
            self._json_ok(self._try(handle_pulse, "pulse"))
            return

        if route == "/api/projects":
            self._json_ok(self._try(handle_projects, "projects"))
            return

        if route == "/api/cron":
            self._json_ok(self._try(handle_cron, "cron"))
            return

        if route == "/api/health":
            self._json_ok(self._try(handle_health, "health"))
            return

        if route == "/api/memories":
            query = qs.get("q", [None])[0]
            self._json_ok(self._try(lambda: handle_memories(query), "memories"))
            return

        if route == "/api/bottlenecks":
            self._json_ok(self._try(handle_bottlenecks, "bottlenecks"))
            return

        if route == "/api/actions":
            self._json_ok(self._try(handle_actions, "actions"))
            return

        # Serve static files
        if self.path in ("/", ""):
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/actions/trigger":
            body = self._read_body()
            action_id = body.get("action", "") if body else ""
            if not action_id:
                self._json_ok(make_error("Missing 'action' in request body"))
                return
            result = self._try(lambda: handle_actions_trigger(action_id, body), "actions")
            self._json_ok(result if isinstance(result, dict) else make_response(result, "actions"))
            return

        # Fallback
        self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        # Only log API calls, suppress static file noise
        try:
            msg = args[0] if args else ""
            if isinstance(msg, str) and '/api/' in msg:
                logger.info(f"API {msg}")
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────

    def _json_ok(self, data):
        """Send a JSON 200 response with CORS headers."""
        body = json.dumps(data, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, status, message):
        """Send a JSON error response."""
        body = json.dumps({"ok": False, "error": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")

    def _read_body(self):
        """Read and parse JSON body."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 1024 * 1024:  # 1MB limit
                return None
            raw = self.rfile.read(length)
            return json.loads(raw.decode()) if raw else {}
        except Exception:
            return None

    def _try(self, func, source="unknown"):
        """Wrap a handler with try/except, returning error envelope on failure."""
        try:
            result = func()
            return make_response(result, source)
        except Exception as e:
            logger.error(f"Handler {source} failed: {e}", exc_info=True)
            return make_error(f"{source}: {e}")

    def _status(self):
        """Return server + gateway status."""
        state = gateway_bridge.get_state()
        snapshot = state.snapshot()
        return {
            "status": "ok",
            "server": {
                "uptime_seconds": round(time.time() - START_TIME),
                "workspace": str(WORKSPACE),
                "version": "2.0.0",
            },
            "gateway": {
                "connected": snapshot.get("connected", False),
                "last_update": snapshot.get("last_update"),
                "error": snapshot.get("error"),
            },
        }


# ── Main ───────────────────────────────────────────────────────

def main():
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555

    # Start gateway bridge
    logger.info("Starting Gateway WebSocket bridge...")
    try:
        gateway_bridge.start_bridge()
        logger.info("Gateway bridge started")
    except Exception as e:
        logger.error(f"Failed to start gateway bridge: {e}")
        # Continue anyway — server works with filesystem-only data

    # Change to project directory for static file serving
    os.chdir(str(SERVER_DIR))

    server = HTTPServer(("127.0.0.1", port), APIHandler)

    # Graceful shutdown
    def shutdown(sig, frame):
        logger.info("Shutting down...")
        gateway_bridge.stop_bridge()
        server.shutdown()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(f"🚀 Mission Control v2 on http://127.0.0.1:{port}")
    logger.info(f"   Workspace: {WORKSPACE}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        gateway_bridge.stop_bridge()
        logger.info("Mission Control stopped")


if __name__ == "__main__":
    main()

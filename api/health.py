"""Health handler — gateway health, channel status, API usage, tunnel status."""
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from gateway_bridge import get_state

CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
TUNNEL_URL_PATH = Path(__file__).resolve().parent.parent / "tunnel-url.txt"


def handle_health():
    """Return comprehensive health status."""
    state = get_state()
    snapshot = state.snapshot()

    # Gateway health
    gateway = {
        "connected": snapshot.get("connected", False),
        "last_update": snapshot.get("last_update"),
        "version": snapshot.get("version"),
        "error": snapshot.get("error"),
    }

    # Channel status
    channels = _get_channel_status(snapshot)

    # API usage
    usage = _get_usage(snapshot)

    # Tunnel status
    tunnel = _get_tunnel_status()

    # Memory/workspace stats
    workspace_stats = _get_workspace_stats()

    # Overall status
    all_healthy = gateway["connected"]
    if channels.get("discord", {}).get("connected") is False:
        all_healthy = False
    if channels.get("telegram", {}).get("connected") is False:
        all_healthy = False

    return {
        "gateway": gateway,
        "channels": channels,
        "usage": usage,
        "tunnel": tunnel,
        "workspace": workspace_stats,
        "all_healthy": all_healthy,
    }


def _get_channel_status(snapshot):
    """Extract channel status from gateway or config."""
    channels = {}

    # Try gateway first
    gw_channels = snapshot.get("channels", {})
    if gw_channels:
        for name, data in gw_channels.items():
            if isinstance(data, dict):
                channels[name] = {
                    "connected": data.get("connected", data.get("status") == "connected"),
                    "name": data.get("name", name),
                    "last_heartbeat": data.get("lastHeartbeat", data.get("lastSeen")),
                    "status": data.get("status", "unknown"),
                }
    else:
        # Fall back to config
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            ch_config = config.get("channels", {})
            for name, data in ch_config.items():
                enabled = data.get("enabled", False)
                channels[name] = {
                    "connected": None,  # Unknown — gateway not connected
                    "name": name,
                    "enabled": enabled,
                    "status": "unknown (no gateway)",
                }
        except Exception:
            pass

    return channels


def _get_usage(snapshot):
    """Extract API usage data."""
    gw_usage = snapshot.get("usage", {})
    if gw_usage:
        return gw_usage

    # Provide minimal structure
    return {
        "note": "No usage data available (gateway disconnected)",
        "windows": [],
    }


def _get_tunnel_status():
    """Check tunnel URL and status."""
    tunnel = {
        "url": None,
        "active": False,
    }
    try:
        if TUNNEL_URL_PATH.exists():
            url = TUNNEL_URL_PATH.read_text().strip()
            if url.startswith("https://"):
                tunnel["url"] = url
                tunnel["active"] = True
    except Exception:
        pass

    # Check if cloudflared process is running
    try:
        result = subprocess.run(
            ["pgrep", "-l", "cloudflared"],
            capture_output=True, text=True, timeout=5
        )
        tunnel["process_running"] = result.returncode == 0
    except Exception:
        tunnel["process_running"] = None

    return tunnel


def _get_workspace_stats():
    """Get workspace size and session count."""
    stats = {
        "workspace_size_mb": 0,
        "session_count": 0,
        "memory_files": 0,
    }

    workspace = Path.home() / ".openclaw" / "workspace"
    try:
        total = 0
        for f in workspace.rglob("*"):
            if f.is_file() and not f.name.startswith('.'):
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        stats["workspace_size_mb"] = round(total / (1024 * 1024), 1)
    except Exception:
        pass

    sessions_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    try:
        if sessions_dir.exists():
            stats["session_count"] = len([f for f in sessions_dir.iterdir()
                                          if f.suffix == '.jsonl' and not f.name.startswith('.')])
    except Exception:
        pass

    memory_dir = workspace / "memory"
    try:
        if memory_dir.exists():
            stats["memory_files"] = len([f for f in memory_dir.rglob("*.md")
                                         if not f.name.startswith('.')])
    except Exception:
        pass

    return stats

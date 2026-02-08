"""
Health Check HTTP Server for The Constituent v6.2
==================================================
Lightweight HTTP endpoint for monitoring and Docker health checks.
Runs on port 8080 (configurable via HEALTH_PORT env var).
No external dependencies — uses stdlib http.server.
"""

import os
import json
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

logger = logging.getLogger("TheConstituent.Health")

_start_time = time.time()
_engine_ref = None
_heartbeat_ref = None


class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for health checks."""

    def do_GET(self):
        if self.path == "/health":
            self._respond_health()
        elif self.path == "/status":
            self._respond_status()
        elif self.path == "/metrics":
            self._respond_metrics()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "not found"}')

    def _respond_health(self):
        """Basic health check — always 200 if server is up."""
        uptime = int(time.time() - _start_time)
        data = {
            "status": "ok",
            "uptime_seconds": uptime,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if _heartbeat_ref:
            hb_status = _heartbeat_ref.get_status()
            data["heartbeat_running"] = hb_status.get("running", False)
            data["heartbeat_ticks"] = hb_status.get("tick_count", 0)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _respond_status(self):
        """Detailed status with engine info."""
        uptime = int(time.time() - _start_time)
        data = {
            "status": "ok",
            "version": "6.2.0",
            "uptime_seconds": uptime,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if _engine_ref:
            try:
                budget = _engine_ref.get_budget_status()
                data["budget"] = budget
                data["tools_count"] = len(_engine_ref.registry.list_tools())
            except Exception:
                pass

        if _heartbeat_ref:
            data["heartbeat"] = _heartbeat_ref.get_status()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _respond_metrics(self):
        """Prometheus-style metrics (text format)."""
        uptime = int(time.time() - _start_time)
        lines = [
            f"# HELP constituent_uptime_seconds Agent uptime in seconds",
            f"# TYPE constituent_uptime_seconds gauge",
            f"constituent_uptime_seconds {uptime}",
        ]

        if _heartbeat_ref:
            hb = _heartbeat_ref.get_status()
            lines.extend([
                f"# HELP constituent_heartbeat_ticks Total heartbeat ticks",
                f"# TYPE constituent_heartbeat_ticks counter",
                f"constituent_heartbeat_ticks {hb.get('tick_count', 0)}",
            ])

        if _engine_ref:
            try:
                budget = _engine_ref.get_budget_status()
                lines.extend([
                    f"# HELP constituent_api_calls_today API calls today",
                    f"# TYPE constituent_api_calls_today gauge",
                    f"constituent_api_calls_today {budget.get('api_calls_today', 0)}",
                    f"# HELP constituent_api_calls_max Daily API call limit",
                    f"# TYPE constituent_api_calls_max gauge",
                    f"constituent_api_calls_max {budget.get('max_per_day', 0)}",
                ])
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("\n".join(lines).encode())

    def log_message(self, format, *args):
        """Suppress default access logs (too noisy for health checks)."""
        pass


def start_health_server(engine=None, heartbeat=None, port: int = None):
    """Start the health check HTTP server in a background thread."""
    global _engine_ref, _heartbeat_ref
    _engine_ref = engine
    _heartbeat_ref = heartbeat

    port = port or int(os.environ.get("HEALTH_PORT", "8080"))

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health server started on port {port}")
    return server

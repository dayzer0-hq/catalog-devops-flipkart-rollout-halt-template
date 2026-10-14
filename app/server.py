"""Flipkart checkout service

BREAK_READINESS=1 is what the 'broken' image tag sets. It starts and never becomes ready.
"""
import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("PORT", "8080"))

# Readiness is not liveness. The process is alive the moment it starts; it can SERVE only once
# its cache is warm. WARMUP_SECONDS is how long that takes.
WARMUP_SECONDS = float(os.environ.get("WARMUP_SECONDS", "5"))

# Set BREAK_READINESS=1 and this never becomes ready — the process stays up and answers
# /healthz, and /readyz never goes green. That is what a broken deploy looks like from the
# outside, and it is how you make a rollout halt on purpose.
BREAK_READINESS = os.environ.get("BREAK_READINESS", "") == "1"

# How long to keep serving after SIGTERM before exiting.
SHUTDOWN_DELAY_SECONDS = float(os.environ.get("SHUTDOWN_DELAY_SECONDS", "0"))

STARTED = time.time()
_shutting_down = threading.Event()


def ready():
    if BREAK_READINESS or _shutting_down.is_set():
        return False
    return (time.time() - STARTED) >= WARMUP_SECONDS


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/healthz":
            body, code = json.dumps({"alive": True}).encode(), 200
        elif path == "/readyz":
            ok = ready()
            body = json.dumps({
                "ready": ok,
                "warmed_for_seconds": round(time.time() - STARTED, 1),
                "warmup_seconds": WARMUP_SECONDS,
                "break_readiness": BREAK_READINESS,
            }).encode()
            code = 200 if ok else 503
        elif path.startswith("/checkout"):
            if not ready():
                body, code = json.dumps({"error": "not ready"}).encode(), 503
            else:
                body, code = json.dumps({"order_id": "FK24101500042", "status": "confirmed"}).encode(), 200
        else:
            body, code = json.dumps({"error": "not found"}).encode(), 404
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def on_sigterm(signum, frame):
    """Leaves the Service's endpoint list before the process dies, if given the chance.

    The delay is configurable so the race is observable: with SHUTDOWN_DELAY_SECONDS=0 the
    process is gone immediately and in-flight requests are lost.
    """
    print(f"SIGTERM received, draining for {SHUTDOWN_DELAY_SECONDS}s", flush=True)
    _shutting_down.set()
    time.sleep(SHUTDOWN_DELAY_SECONDS)
    print("exiting", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, on_sigterm)
    print(f"Flipkart checkout service listening on {PORT}, warmup={WARMUP_SECONDS}s, break_readiness={BREAK_READINESS}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

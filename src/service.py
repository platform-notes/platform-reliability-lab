"""Small observability demonstration using only Python's standard library."""
import json
import os
import signal
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)

class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {}
        self.durations = {}

    def observe(self, method, route, status, duration):
        key = (method, route, str(status))
        hist_key = (method, route)

        with self.lock:
            self.counts[key] = self.counts.get(key, 0) + 1

            hist = self.durations.setdefault(
                hist_key,
                {
                    "count": 0,
                    "sum": 0.0,
                    "buckets": [0] * len(BUCKETS),
                },
            )

            hist["count"] += 1
            hist["sum"] += duration

            for i, bound in enumerate(BUCKETS):
                if duration <= bound:
                    hist["buckets"][i] += 1

    def render(self):
        with self.lock:
            counts = dict(self.counts)
            durations = {
                key: {
                    "count": value["count"],
                    "sum": value["sum"],
                    "buckets": value["buckets"].copy(),
                }
                for key, value in self.durations.items()
            }

        rows = [
            "# HELP demo_http_requests_total Total HTTP requests.",
            "# TYPE demo_http_requests_total counter",
        ]

        for (method, route, status), value in sorted(counts.items()):
            rows.append(
                f'demo_http_requests_total{{method="{method}",'
                f'route="{route}",status="{status}"}} {value}'
            )

        rows += [
            "# HELP demo_http_duration_seconds Request latency in seconds.",
            "# TYPE demo_http_duration_seconds histogram",
        ]

        for (method, route), hist in sorted(durations.items()):
            labels = f'method="{method}",route="{route}"'

            for bound, count in zip(BUCKETS, hist["buckets"]):
                rows.append(
                    f'demo_http_duration_seconds_bucket'
                    f'{{{labels},le="{bound}"}} {count}'
                )

            rows.append(
                f'demo_http_duration_seconds_bucket'
                f'{{{labels},le="+Inf"}} {hist["count"]}'
            )
            rows.append(
                f'demo_http_duration_seconds_sum'
                f'{{{labels}}} {hist["sum"]:.9f}'
            )
            rows.append(
                f'demo_http_duration_seconds_count'
                f'{{{labels}}} {hist["count"]}'
            )

        return "\n".join(rows) + "\n"

METRICS = Metrics()

class BoundedHTTPServer(ThreadingHTTPServer):
    """Bound concurrent handlers and allow them to finish during shutdown."""

    daemon_threads = False

    def __init__(self, address, handler, max_connections=64):
        if not 1 <= max_connections <= 4096:
            raise ValueError("MAX_CONNECTIONS must be between 1 and 4096")
        self.connection_limit = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self.connection_limit.acquire(blocking=False):
            try:
                request.settimeout(1)
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Connection: close\r\nContent-Length: 0\r\n\r\n"
                )
            except (OSError, socket.timeout):
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.connection_limit.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connection_limit.release()


class Handler(BaseHTTPRequestHandler):
    timeout = 10
    def do_GET(self):
        start = time.perf_counter()
        route = urlsplit(self.path).path
        request_id = str(uuid.uuid4())
        status = 200
        if route == '/healthz':
            body = b'{"status":"ok"}\n'
            content_type = 'application/json'
        elif route == '/metrics':
            body = METRICS.render().encode('utf-8')
            content_type = 'text/plain; version=0.0.4; charset=utf-8'
        elif route == '/':
            body = b'{"service":"platform-reliability-lab","status":"ok"}\n'
            content_type = 'application/json'
        elif route == '/failure' and os.getenv('ENABLE_FAILURE_ENDPOINT') == 'true':
            status = 500
            body = b'{"error":"controlled_failure"}\n'
            content_type = 'application/json'
        else:
            status = 404
            body = b'{"error":"not_found"}\n'
            content_type = 'application/json'
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Request-ID', request_id)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected; still record the server-side outcome.
        finally:
            duration = max(time.perf_counter() - start, 0)
            if route != '/metrics':
                METRICS.observe('GET', route if route in ('/', '/healthz', '/failure') else 'unmatched', status, duration)
                print(json.dumps({'event':'request','request_id':request_id,'route':route,'status':status,'duration_ms':round(duration*1000,3)}), flush=True)

    def log_message(self, format, *args):
        pass  # avoid duplicating structured request logs


def main():
    port = int(os.getenv('PORT', '8080'))
    max_connections = int(os.getenv('MAX_CONNECTIONS', '64'))
    server = BoundedHTTPServer(('0.0.0.0', port), Handler, max_connections)

    def request_shutdown(signum, frame):
        # shutdown() cannot run on the same thread as serve_forever().
        threading.Thread(target=server.shutdown, daemon=True).start()

    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for sig in previous:
            signal.signal(sig, request_shutdown)
        print(json.dumps({'event': 'start', 'port': port}), flush=True)
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()  # Join non-daemon request threads before closing.
        for sig, handler in previous.items():
            signal.signal(sig, handler)

if __name__ == '__main__':
    main()

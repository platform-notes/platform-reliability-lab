import io
import json
import os
import threading
import unittest
from contextlib import redirect_stdout
from http.client import HTTPConnection
from http.server import HTTPServer
from unittest.mock import patch
from uuid import UUID

from src import service


class HTTPTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop("ENABLE_FAILURE_ENDPOINT", None)

        metrics = patch.object(service, "METRICS", service.Metrics())
        metrics.start()
        self.addCleanup(metrics.stop)

        self.captured_stdout = io.StringIO()
        output = redirect_stdout(self.captured_stdout)
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

        # Handle requests serially so observation finishes before the next scrape.
        self.server = HTTPServer(("127.0.0.1", 0), service.Handler)
        self.server.failure_endpoint_enabled = False
        self.addCleanup(self.server.server_close)
        thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.01}
        )
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)

    def get(self, path, status, content_type):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request("GET", path)
            with connection.getresponse() as response:
                body = response.read()
                self.assertEqual(response.status, status)
                self.assertEqual(response.getheader("Content-Type"), content_type)
                self.assertEqual(response.getheader("Content-Length"), str(len(body)))
                request_id = response.getheader("X-Request-ID")
                self.assertIsNotNone(request_id)
                self.assertEqual(UUID(request_id).version, 4)
                return body, request_id
        finally:
            connection.close()

    def assert_json(self, path, status, expected):
        body, request_id = self.get(path, status, "application/json")
        self.assertEqual(json.loads(body), expected)
        return request_id

    def scrape(self):
        body, _ = self.get("/metrics", 200, "text/plain; version=0.0.4; charset=utf-8")
        return body.decode("utf-8").splitlines()

    def test_root(self):
        self.assert_json("/", 200, {"service": "platform-reliability-lab", "status": "ok"})

    def test_health(self):
        first = self.assert_json("/healthz", 200, {"status": "ok"})
        second = self.assert_json("/healthz", 200, {"status": "ok"})
        self.assertNotEqual(first, second)

    def test_metrics_endpoint(self):
        rows = self.scrape()
        self.assertIn("# TYPE demo_http_requests_total counter", rows)
        self.assertIn("# TYPE demo_http_duration_seconds histogram", rows)

    def test_unknown_route(self):
        self.assert_json("/missing", 404, {"error": "not_found"})

    def test_failure_endpoint_disabled(self):
        for setting in (None, "false"):
            with self.subTest(setting=setting):
                if setting is not None:
                    os.environ["ENABLE_FAILURE_ENDPOINT"] = setting
                self.assert_json("/failure", 404, {"error": "not_found"})

    def test_failure_endpoint_enabled(self):
        self.server.failure_endpoint_enabled = True
        self.assert_json("/failure", 500, {"error": "controlled_failure"})

    def test_metrics_preserve_counters_and_histograms_across_scrapes(self):
        self.get("/healthz", 200, "application/json")
        self.get("/healthz", 200, "application/json")
        self.get("/missing", 404, "application/json")
        rows = self.scrape()
        for route, status, count in (("/healthz", 200, 2), ("unmatched", 404, 1)):
            with self.subTest(route=route):
                labels = f'method="GET",route="{route}"'
                self.assertIn(
                    f'demo_http_requests_total{{{labels},status="{status}"}} {count}', rows
                )
                self.assertIn(f"demo_http_duration_seconds_count{{{labels}}} {count}", rows)
                self.assertIn(
                    f'demo_http_duration_seconds_bucket{{{labels},le="+Inf"}} {count}', rows
                )
        self.assertEqual(self.scrape(), rows)

    def test_failure_disabled_counts_unmatched(self):
        self.assert_json('/failure', 404, {'error': 'not_found'})
        self.assertIn('demo_http_requests_total{method="GET",route="unmatched",status="404"} 1', self.scrape())

    def test_sensitive_path_never_logged(self):
        self.assert_json('/secret-api-token-please-hide?token=hidden', 404, {'error': 'not_found'})
        self.assertIn('demo_http_requests_total{method="GET",route="unmatched",status="404"} 1', self.scrape())
        # Handler emits resolved labels only; no raw user-controlled path.
        self.assertNotIn('secret-api-token-please-hide', service.METRICS.render())
        self.assertNotIn('secret-api-token-please-hide', self.captured_stdout.getvalue())
        self.assertNotIn('token=hidden', self.captured_stdout.getvalue())

    def test_server_header_excludes_python(self):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request('GET', '/healthz')
            response = connection.getresponse()
            self.assertNotIn('Python', response.getheader('Server'))
            response.read()
        finally:
            connection.close()

    def test_failure_flag_is_cached_at_server_creation(self):
        self.server.failure_endpoint_enabled = False
        os.environ['ENABLE_FAILURE_ENDPOINT'] = 'true'
        self.assert_json('/failure', 404, {'error': 'not_found'})
        self.server.failure_endpoint_enabled = True
        os.environ['ENABLE_FAILURE_ENDPOINT'] = 'false'
        self.assert_json('/failure', 500, {'error': 'controlled_failure'})

import unittest
from unittest.mock import Mock
from src.service import BoundedHTTPServer, Handler
from src.service import BUCKETS, Metrics

class MetricsTests(unittest.TestCase):
    def test_counter_and_histogram(self):
        m = Metrics()
        m.observe('GET', '/', 200, 0.012)
        m.observe('GET', '/', 500, 0.300)
        data = m.render()
        self.assertIn('status="200"} 1', data)
        self.assertIn('status="500"} 1', data)
        self.assertIn('le="0.025"} 1', data)
        self.assertIn('le="+Inf"} 2', data)
        self.assertIn('demo_http_duration_seconds_count{method="GET",route="/"} 2', data)

    def test_histogram_bounded_memory(self):
        m = Metrics()

        for _ in range(100_000):
            m.observe("GET", "/", 200, 0.012)

        hist = m.durations[("GET", "/")]

        self.assertEqual(hist["count"], 100_000)
        self.assertEqual(len(hist["buckets"]), len(BUCKETS))
        self.assertEqual(
            hist["buckets"][BUCKETS.index(0.025)],
            100_000,
        )
        self.assertIn(
            'demo_http_duration_seconds_count'
            '{method="GET",route="/"} 100000',
            m.render(),
        )

    def test_empty_registry(self):
        self.assertIn('demo_http_requests_total', Metrics().render())

    def test_bucket_order(self):
        self.assertEqual(tuple(sorted(BUCKETS)), BUCKETS)

class ConnectionLimitTests(unittest.TestCase):
    def test_handler_timeout(self):
        self.assertEqual(Handler.timeout, 10)

    def test_connection_rejected_when_all_slots_held(self):
        server = BoundedHTTPServer(('127.0.0.1', 0), Handler, max_connections=1)
        try:
            self.assertTrue(server.connection_limit.acquire(blocking=False))
            peer = Mock()
            server.process_request(peer, ('127.0.0.1', 1))
            self.assertIn(b'503 Service Unavailable', peer.sendall.call_args.args[0])
            peer.close.assert_called_once()
            server.connection_limit.release()
        finally:
            server.server_close()

    def test_slot_released_even_on_handler_failure(self):
        server = BoundedHTTPServer(('127.0.0.1', 0), Handler, max_connections=1)
        try:
            server.connection_limit.acquire()
            from unittest.mock import patch
            with patch('http.server.ThreadingHTTPServer.process_request_thread', side_effect=RuntimeError):
                with self.assertRaises(RuntimeError):
                    server.process_request_thread(Mock(), ('127.0.0.1', 1))
            self.assertTrue(server.connection_limit.acquire(blocking=False))
            server.connection_limit.release()
        finally:
            server.server_close()

    def test_shutdown_waits_for_inflight_response(self):
        import threading
        import time
        from http.client import HTTPConnection

        started = threading.Event()
        release = threading.Event()
        received = []
        errors = []

        class SlowHandler(Handler):
            def do_GET(self):
                started.set()
                if not release.wait(3):
                    raise TimeoutError("test handler was never released")
                super().do_GET()

        server = BoundedHTTPServer(('127.0.0.1', 0), SlowHandler, max_connections=1)
        serving = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
        serving.start()

        def read_response():
            connection = HTTPConnection(*server.server_address, timeout=4)
            try:
                connection.request('GET', '/healthz')
                with connection.getresponse() as response:
                    received.append((response.status, response.read()))
            except Exception as exc:
                errors.append(exc)
            finally:
                connection.close()

        client = threading.Thread(target=read_response)
        client.start()
        stopper = None
        closer = None
        try:
            self.assertTrue(started.wait(2), 'request never reached handler')
            stopper = threading.Thread(target=server.shutdown)
            stopper.start()
            stopper.join(timeout=2)
            self.assertFalse(stopper.is_alive(), 'serve_forever did not stop')
            closer = threading.Thread(target=server.server_close)
            closer.start()
            time.sleep(0.05)
            self.assertTrue(closer.is_alive(), 'server_close must wait for active handler')
            release.set()
            client.join(timeout=3)
            closer.join(timeout=3)
            self.assertFalse(client.is_alive())
            self.assertFalse(closer.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(received, [(200, b'{"status":"ok"}\n')])
        finally:
            release.set()
            server.shutdown()
            server.server_close()
            serving.join(timeout=2)
            client.join(timeout=2)
            if stopper is not None:
                stopper.join(timeout=2)
            if closer is not None:
                closer.join(timeout=2)

    def test_shutdown_completes(self):
        import threading
        server = BoundedHTTPServer(('127.0.0.1', 0), Handler, max_connections=1)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01})
        thread.start()
        try:
            stopper = threading.Thread(target=server.shutdown)
            stopper.start()
            stopper.join(timeout=2)
            thread.join(timeout=2)
            self.assertFalse(stopper.is_alive())
            self.assertFalse(thread.is_alive())
        finally:
            server.shutdown()
            server.server_close()

class MetricLabelValidationTests(unittest.TestCase):
    def test_rejects_unsafe_labels_and_invalid_duration(self):
        for args in [
            ('GET', '/private/token', 200, .1),
            ('POST', '/', 200, .1),
            ('GET', '/', 200, float('nan')),
            ('GET', '/', 200, -1),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Metrics().observe(*args)

if __name__ == '__main__':
    unittest.main()

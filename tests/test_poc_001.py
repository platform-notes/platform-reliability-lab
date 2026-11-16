import json
import unittest
from unittest.mock import mock_open, patch

from poc_001 import readiness


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tools = readiness.ReadinessTools()
        self.params = {
            "scenario": "not_ready",
            "namespace": "fictional-lab",
            "pod": "demo-blocked",
            "timeout_ms": 100,
        }

    def diagnose(self, scenario, pod):
        return readiness.diagnose(
            self.tools, scenario=scenario, namespace="fictional-lab", pod=pod, service="demo-web"
        )

    def test_running_not_ready(self):
        result = self.diagnose("not_ready", "demo-blocked")
        self.assertEqual(result["outcome"], "running_not_ready")
        status, events, endpoints = [item["evidence"] for item in result["evidence"]]
        self.assertEqual(status, {"phase": "Running", "ready": False})
        self.assertEqual(events[0]["reason"], "Unhealthy")
        self.assertEqual(endpoints, [{"pod": "demo-blocked", "ready": False}])

    def test_healthy_service(self):
        result = self.diagnose("healthy", "demo-healthy")
        self.assertEqual(result["outcome"], "healthy")
        self.assertEqual([item["state"] for item in result["evidence"]], ["ok"] * 3)
        self.assertEqual(result["evidence"][1]["evidence"], [])

    def test_insufficient_evidence(self):
        result = self.diagnose("incomplete", "demo-unknown")
        self.assertEqual(result["outcome"], "insufficient_evidence")
        self.assertEqual(
            [item["state"] for item in result["evidence"]],
            ["ok", "missing_evidence", "missing_evidence"],
        )

    def test_invalid_parameters(self):
        for params in (
            None,
            {},
            {**self.params, "path": "/tmp/data.json"},
            {**self.params, "pod": "../demo"},
            {**self.params, "namespace": "a" * 64},
            {**self.params, "scenario": []},
            {**self.params, "timeout_ms": True},
            {**self.params, "timeout_ms": 0},
            {**self.params, "timeout_ms": 1001},
        ):
            with self.subTest(params=params):
                self.assertEqual(self.tools.get_pod_status(params)["state"], "invalid_input")

    def test_unknown_resource(self):
        result = self.tools.get_events({**self.params, "pod": "other-pod"})
        self.assertEqual(result, {"tool": "get_events", "state": "not_found", "evidence": None})

    def test_expired_timeout(self):
        with patch.object(readiness, "monotonic", side_effect=[0, 1]):
            self.assertEqual(self.tools.get_pod_status(self.params)["state"], "timeout")

    def test_invalid_fixture(self):
        source = readiness._FIXTURE.read_text(encoding="utf-8")
        wrong_type = json.loads(source)
        wrong_type["not_ready"]["status"]["ready"] = "false"
        for raw in (b"{", b"{}", b'{"a":1,"a":2}', json.dumps(wrong_type).encode()):
            with self.subTest(raw=raw):
                with patch.object(readiness.Path, "open", mock_open(read_data=raw)):
                    tools = readiness.ReadinessTools()
                self.assertEqual(tools.get_pod_status(self.params)["state"], "invalid_fixture")

    def test_unavailable_fixture(self):
        with patch.object(readiness.Path, "open", side_effect=FileNotFoundError):
            tools = readiness.ReadinessTools()
        self.assertEqual(tools.get_pod_status(self.params)["state"], "fixture_unavailable")

    def test_evidence_cannot_mutate_snapshot(self):
        self.tools.get_events(self.params)["evidence"].clear()
        self.assertEqual(len(self.tools.get_events(self.params)["evidence"]), 1)

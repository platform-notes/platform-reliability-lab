import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

from poc_001 import readiness
from poc_001.__main__ import main
from poc_001.assistant import InvalidIncident, run_incident
from poc_001.evidence import TOOL_NAMES, build_catalog


CASES = (
    ("not_ready", "demo-blocked", "running_not_ready"),
    ("healthy", "demo-healthy", "healthy"),
    ("incomplete", "demo-unknown", "insufficient_evidence"),
)


def incident(scenario="not_ready", pod="demo-blocked", identifier="test"):
    return dict(incident_id=identifier, scenario=scenario, namespace="fictional-lab",
                pod=pod, service="demo-web")


def cli_args(data):
    return [argument for key, value in data.items()
            for argument in ("--" + key.replace("_", "-"), value)]


class AssistantTests(unittest.TestCase):
    def test_classification_and_raw_results_match_reference(self):
        for scenario, pod, expected in CASES:
            with self.subTest(scenario=scenario):
                result = run_incident(incident(scenario, pod))
                reference = readiness.diagnose(
                    readiness.ReadinessTools(), scenario=scenario, namespace="fictional-lab",
                    pod=pod, service="demo-web",
                )
                self.assertEqual(result["diagnosis"]["classification"], expected)
                self.assertEqual(result["diagnosis"]["classification"], reference["outcome"])
                self.assertEqual(list(result["diagnosis"]["raw_results"].values()),
                                 reference["evidence"])
                self.assertEqual(result["diagnosis"]["source"], "deterministic")
                self.assertEqual(result["ai"], {"state": "not_used"})
                self.assertEqual(result["errors"], [])

    def test_collector_calls_each_tool_once_and_reuses_results(self):
        real_tools = readiness.ReadinessTools()
        spy = Mock(spec=readiness.ReadinessTools, wraps=real_tools)
        with patch.object(readiness, "ReadinessTools", return_value=spy), patch.object(
            readiness, "diagnose", wraps=readiness.diagnose
        ) as engine:
            data = incident()
            result = run_incident(data)
        engine.assert_called_once()
        replay = engine.call_args.args[0]
        common = {"scenario": "not_ready", "namespace": "fictional-lab", "timeout_ms": 100}
        for source, target in zip(TOOL_NAMES, ({"pod": data["pod"]}, {"pod": data["pod"]},
                                                {"service": data["service"]})):
            params = {**common, **target}
            getattr(spy, source).assert_called_once_with(params)
            snapshot = result["diagnosis"]["raw_results"][source]
            self.assertEqual(getattr(replay, source)(params), snapshot)
            getattr(replay, source)(params)["state"] = "changed"
            self.assertEqual(getattr(replay, source)(params), snapshot)

    def test_report_uses_engine_outcome(self):
        with patch.object(readiness, "diagnose", return_value={"outcome": "healthy"}):
            report = run_incident(incident())
        self.assertEqual(report["diagnosis"]["classification"], "healthy")
        self.assertFalse(report["observations"][0]["value"]["ready"])

    def test_incomplete_has_distinct_gaps_and_observed_pod(self):
        report = run_incident(incident("incomplete", "demo-unknown"))
        self.assertEqual(report["observations"][0]["value"], {"phase": "Running", "ready": False})
        self.assertEqual([item["source"] for item in report["gaps"]],
                         ["get_events", "get_endpoints"])
        for item in report["observations"][1:]:
            self.assertEqual((item["kind"], item["state"], item["value"]),
                             ("gap", "missing_evidence", "missing_evidence"))
        self.assertEqual(report["errors"], [])

    def test_diagnosis_ids_reference_only_supporting_observations(self):
        expected = {
            "not_ready": ["test:1", "test:2", "test:3"],
            "healthy": ["test:1", "test:3"],
            "incomplete": [],
        }
        for scenario, pod, _ in CASES:
            with self.subTest(scenario=scenario):
                report = run_incident(incident(scenario, pod))
                self.assertEqual(report["diagnosis"]["evidence_ids"], expected[scenario])
                self.assertEqual([item["id"] for item in report["observations"]],
                                 ["test:1", "test:2", "test:3"])
                quality = "missing_evidence" if scenario == "incomplete" else "complete"
                self.assertEqual(report["collection_quality"], quality)

    def test_empty_events_are_observed(self):
        report = run_incident(incident("healthy", "demo-healthy"))
        event = report["observations"][1]
        self.assertEqual((event["kind"], event["state"], event["value"]), ("events", "ok", []))
        self.assertEqual(report["gaps"], [])

    def test_invalid_input_collects_nothing(self):
        for changes in ({"namespace": "../other"}, {"pod": 1}, {"scenario": []},
                        {"incident_id": "bad:id"}, {"extra": "field"}):
            with self.subTest(changes=changes), patch.object(readiness, "ReadinessTools") as tools:
                with self.assertRaises(InvalidIncident):
                    run_incident({**incident(), **changes})
                tools.assert_not_called()

    def test_fixture_unavailable_and_timeout_are_errors(self):
        for exception, state in ((FileNotFoundError, "fixture_unavailable"),
                                 (TimeoutError, "timeout")):
            with self.subTest(state=state), patch.object(readiness.Path, "open", side_effect=exception):
                result = run_incident(incident())
            self.assertEqual(result["diagnosis"]["classification"], "insufficient_evidence")
            self.assertEqual(result["gaps"], [])
            self.assertEqual([item["state"] for item in result["errors"]], [state] * 3)
            self.assertEqual([item["value"] for item in result["observations"]], [state] * 3)

    def test_tool_timeout_preserves_other_collected_results(self):
        with patch.object(readiness, "monotonic", side_effect=(0, 1, 2, 2, 3, 3)):
            result = run_incident(incident())
        self.assertEqual(result["diagnosis"]["classification"], "insufficient_evidence")
        self.assertEqual([item["state"] for item in result["observations"]], ["timeout", "ok", "ok"])
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["evidence_id"], "test:1")
        self.assertEqual(result["collection_quality"], "operational_error")
        self.assertEqual(result["diagnosis"]["evidence_ids"], [])

    def test_error_takes_precedence_without_hiding_gaps(self):
        with patch.object(readiness, "monotonic", side_effect=(0, 1, 2, 2, 3, 3)):
            result = run_incident(incident("incomplete", "demo-unknown"))
        self.assertEqual(result["collection_quality"], "operational_error")
        self.assertEqual(result["diagnosis"]["classification"], "insufficient_evidence")
        self.assertEqual(result["diagnosis"]["evidence_ids"], [])
        self.assertEqual(result["errors"], [
            {"source": "get_pod_status", "state": "timeout", "evidence_id": "test:1"},
        ])
        self.assertEqual(result["gaps"], [
            {"source": "get_events", "state": "missing_evidence", "evidence_id": "test:2"},
            {"source": "get_endpoints", "state": "missing_evidence", "evidence_id": "test:3"},
        ])

    def test_collecting_unknown_pod_preserves_not_found(self):
        result = run_incident(incident(pod="other"))
        self.assertEqual(result["diagnosis"]["classification"], "insufficient_evidence")
        self.assertEqual([item["state"] for item in result["observations"]],
                         ["not_found", "not_found", "ok"])
        self.assertEqual(len(result["errors"]), 2)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.results = run_incident(incident())["diagnosis"]["raw_results"]
        self.catalog = build_catalog("test", self.results)

    def test_order_and_ids(self):
        reversed_input = dict(reversed(list(self.results.items())))
        self.assertEqual(self.catalog, build_catalog("test", reversed_input))
        other = build_catalog("other", self.results)
        self.assertTrue({x.id for x in self.catalog.observations}.isdisjoint(
            x.id for x in other.observations
        ))
        with self.assertRaises(KeyError):
            self.catalog.resolve(other.observations[0].id)

    def test_catalog_has_no_mutable_shared_state(self):
        observation = self.catalog.observations[0]
        self.results["get_pod_status"]["evidence"]["ready"] = True
        observation.value["ready"] = True
        self.catalog.raw_results()["get_pod_status"]["evidence"]["ready"] = True
        self.assertFalse(observation.value["ready"])
        with self.assertRaises(FrozenInstanceError):
            observation.state = "timeout"
        with self.assertRaises(FrozenInstanceError):
            self.catalog.observations = ()

    def test_trace_links_resolve_to_observed_fields(self):
        report = run_incident(incident())
        for observation in report["observations"]:
            node = report
            for segment in observation["raw_ref"].split("/")[1:]:
                node = node[segment]
            values = tuple(node[path[1:]] for path in observation["paths"])
            self.assertEqual(values, self.catalog.resolve(observation["id"]))
            self.assertEqual(values, (observation["value"],))
        with self.assertRaises(KeyError):
            self.catalog.resolve("/etc/passwd")
        with self.assertRaises(ValueError):
            build_catalog("test", {"get_pod_status": self.results["get_pod_status"]})


class CLITests(unittest.TestCase):
    def test_scenarios_do_not_use_socket_or_model(self):
        for scenario, pod, expected in CASES:
            stdout, stderr = io.StringIO(), io.StringIO()
            with self.subTest(scenario=scenario), redirect_stdout(stdout), redirect_stderr(stderr):
                with patch("socket.socket", side_effect=AssertionError("unexpected network")):
                    status = main(cli_args(incident(scenario, pod)))
            self.assertEqual(status, 0)
            report = json.loads(stdout.getvalue())
            self.assertEqual(report["diagnosis"]["classification"], expected)
            self.assertEqual(report["ai"], {"state": "not_used"})
            self.assertEqual(stderr.getvalue(), "")

    def test_operational_and_argument_errors(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(cli_args(incident(pod="other"))), 1)
        self.assertTrue(json.loads(stdout.getvalue())["errors"])
        self.assertEqual(stderr.getvalue(), "")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
            main(cli_args(incident(pod="../other")))
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("pod must be a DNS label", stderr.getvalue())

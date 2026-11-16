"""Read-only tools and reference diagnosis for fictional readiness snapshots."""

import json
import re
from copy import deepcopy
from pathlib import Path
from time import monotonic

_FIXTURE = Path(__file__).with_name("fixtures") / "readiness.json"
_MAX_BYTES = 16_384
_SCENARIOS = ("not_ready", "healthy", "incomplete")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_PHASES = ("Pending", "Running", "Succeeded", "Failed", "Unknown")


def _label(value):
    return type(value) is str and len(value) <= 63 and _LABEL.fullmatch(value) is not None


def _fields(value, *keys):
    return type(value) is dict and value.keys() == set(keys)


def _event(value):
    return _fields(value, "reason", "message") and all(
        type(field) is str and 0 < len(field) <= 256 for field in value.values()
    )


def _endpoint(value):
    return (
        _fields(value, "pod", "ready")
        and _label(value["pod"])
        and type(value["ready"]) is bool
    )


def _optional_list(value, validate):
    return value is None or (
        type(value) is list and len(value) <= 32 and all(map(validate, value))
    )


def _valid_snapshot(value):
    if not _fields(value, "namespace", "pod", "service", "status", "events", "endpoints"):
        return False
    status = value["status"]
    return (
        all(_label(value[key]) for key in ("namespace", "pod", "service"))
        and _fields(status, "phase", "ready")
        and status["phase"] in _PHASES
        and type(status["ready"]) is bool
        and _optional_list(value["events"], _event)
        and _optional_list(value["endpoints"], _endpoint)
    )


def _unique_keys(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate JSON keys")
    return result


def _load_fixture():
    with _FIXTURE.open("rb") as fixture:
        raw = fixture.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise ValueError("Fixture exceeds size limit")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys)
    if not _fields(data, *_SCENARIOS) or not all(map(_valid_snapshot, data.values())):
        raise ValueError("Invalid fixture schema")
    return data


def _result(tool, state, evidence=None):
    return {"tool": tool, "state": state, "evidence": evidence}


class ReadinessTools:
    """Load repository data once, then serve bounded in-memory lookups."""

    def __init__(self):
        self._snapshots = {}
        self._load_error = None
        try:
            self._snapshots = _load_fixture()
        except TimeoutError:
            self._load_error = "timeout"
        except OSError:
            self._load_error = "fixture_unavailable"
        except (ValueError, RecursionError):
            self._load_error = "invalid_fixture"

    def get_pod_status(self, params):
        return self._lookup("get_pod_status", params, "pod", "status")

    def get_events(self, params):
        return self._lookup("get_events", params, "pod", "events")

    def get_endpoints(self, params):
        return self._lookup("get_endpoints", params, "service", "endpoints")

    def _lookup(self, tool, params, resource, field):
        if not _fields(params, "scenario", "namespace", resource, "timeout_ms"):
            return _result(tool, "invalid_input")
        scenario = params["scenario"]
        timeout_ms = params["timeout_ms"]
        if (
            type(scenario) is not str
            or scenario not in _SCENARIOS
            or not _label(params["namespace"])
            or not _label(params[resource])
            or type(timeout_ms) is not int
            or not 1 <= timeout_ms <= 1000
        ):
            return _result(tool, "invalid_input")
        deadline = monotonic() + timeout_ms / 1000
        try:
            if self._load_error:
                return _result(tool, self._load_error)
            snapshot = self._snapshots[scenario]
            if any(snapshot[key] != params[key] for key in ("namespace", resource)):
                result = _result(tool, "not_found")
            elif snapshot[field] is None:
                result = _result(tool, "missing_evidence")
            else:
                result = _result(tool, "ok", deepcopy(snapshot[field]))
            return _result(tool, "timeout") if monotonic() >= deadline else result
        except TimeoutError:
            return _result(tool, "timeout")


def diagnose(tools, *, scenario, namespace, pod, service, timeout_ms=100):
    """Compare three observations from the same fictional snapshot."""
    common = {"scenario": scenario, "namespace": namespace, "timeout_ms": timeout_ms}
    status = tools.get_pod_status({**common, "pod": pod})
    events = tools.get_events({**common, "pod": pod})
    endpoints = tools.get_endpoints({**common, "service": service})
    evidence = [status, events, endpoints]
    outcome = "insufficient_evidence"

    if all(item["state"] == "ok" for item in evidence):
        pod_status = status["evidence"]
        ready_endpoints = [item for item in endpoints["evidence"] if item["ready"]]
        probe_failed = any(
            item["reason"] == "Unhealthy"
            and item["message"].startswith("Readiness probe failed:")
            for item in events["evidence"]
        )
        if (
            pod_status == {"phase": "Running", "ready": False}
            and probe_failed
            and not ready_endpoints
        ):
            outcome = "running_not_ready"
        elif pod_status == {"phase": "Running", "ready": True} and any(
            item["pod"] == pod for item in ready_endpoints
        ):
            outcome = "healthy"

    return {"outcome": outcome, "evidence": evidence}

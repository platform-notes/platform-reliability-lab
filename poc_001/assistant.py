"""Collect a fictional snapshot and report the existing deterministic diagnosis."""

import re
from time import monotonic

from . import readiness
from .evidence import TOOL_NAMES, build_catalog

_INCIDENT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}")
_FIELDS = {"incident_id", "scenario", "namespace", "pod", "service"}
_TIMEOUT_MS = 100
# Attribution for an outcome already decided by diagnose().
_SUPPORTING_SOURCES = {
    "running_not_ready": TOOL_NAMES,
    "healthy": ("get_pod_status", "get_endpoints"),
}


class InvalidIncident(ValueError):
    """The supplied incident cannot be collected."""


def _validate_incident(incident):
    if type(incident) is not dict or incident.keys() != _FIELDS:
        raise InvalidIncident("Expected incident_id, scenario, namespace, pod and service")
    identifier = incident["incident_id"]
    if type(identifier) is not str or len(identifier) > 32 or not _INCIDENT_ID.fullmatch(identifier):
        raise InvalidIncident("incident_id must be 1–32 ASCII letters, digits, underscores or hyphens")
    if type(incident["scenario"]) is not str or incident["scenario"] not in readiness._SCENARIOS:
        raise InvalidIncident("scenario must be not_ready, healthy or incomplete")
    for name in ("namespace", "pod", "service"):
        if not readiness._label(incident[name]):
            raise InvalidIncident(f"{name} must be a DNS label of up to 63 characters")


class _CollectedTools:
    def __init__(self, catalog):
        self._catalog = catalog

    def get_pod_status(self, params):
        return self._catalog.result("get_pod_status")

    def get_events(self, params):
        return self._catalog.result("get_events")

    def get_endpoints(self, params):
        return self._catalog.result("get_endpoints")


def run_incident(incident):
    """Produce the report for one incident using only the bundled fixture."""
    started = monotonic()
    _validate_incident(incident)
    incident = dict(incident)
    target = {key: incident[key] for key in ("scenario", "namespace", "pod", "service")}
    common = {"scenario": target["scenario"], "namespace": target["namespace"],
              "timeout_ms": _TIMEOUT_MS}
    tools = readiness.ReadinessTools()
    collected = {}
    durations = {}
    for name, resource in zip(TOOL_NAMES, ("pod", "pod", "service")):
        before = monotonic()
        collected[name] = getattr(tools, name)({**common, resource: target[resource]})
        durations[name] = (monotonic() - before) * 1000

    catalog = build_catalog(incident["incident_id"], collected)
    outcome = readiness.diagnose(_CollectedTools(catalog), **target, timeout_ms=_TIMEOUT_MS)
    classification = outcome["outcome"]
    supporting_sources = _SUPPORTING_SOURCES.get(classification, ())
    gaps = []
    errors = []
    for entry in catalog.observations:
        detail = {"source": entry.source, "state": entry.state, "evidence_id": entry.id}
        if entry.kind == "gap":
            gaps.append(detail)
        elif entry.kind == "collection_error":
            errors.append(detail)
    if errors:
        collection_quality = "operational_error"
    elif gaps:
        collection_quality = "missing_evidence"
    else:
        collection_quality = "complete"

    return {
        "schema_version": 1,
        "incident": incident,
        "mode": "deterministic",
        "collection_quality": collection_quality,
        "diagnosis": {
            "classification": classification,
            "source": "deterministic",
            "evidence_ids": [
                entry.id for entry in catalog.observations
                if entry.state == "ok" and entry.source in supporting_sources
            ],
            "raw_results": catalog.raw_results(),
        },
        "observations": [entry.as_dict() for entry in catalog.observations],
        "gaps": gaps,
        "errors": errors,
        "ai": {"state": "not_used"},
        "timings": {"tool_ms": durations, "total_ms": (monotonic() - started) * 1000},
    }

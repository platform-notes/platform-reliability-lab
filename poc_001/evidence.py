"""Immutable observations over the three local tool results."""

import json
from dataclasses import dataclass

TOOL_NAMES = ("get_pod_status", "get_events", "get_endpoints")
_KINDS = dict(zip(TOOL_NAMES, ("pod_status", "events", "endpoints")))


@dataclass(frozen=True, slots=True)
class Observation:
    id: str
    kind: str
    source: str
    state: str
    _value_json: str
    raw_ref: str
    paths: tuple[str, ...]

    @property
    def value(self):
        return json.loads(self._value_json)

    def as_dict(self):
        return {
            "id": self.id,
            "kind": self.kind,
            "source": self.source,
            "state": self.state,
            "value": self.value,
            "raw_ref": self.raw_ref,
            "paths": list(self.paths),
        }


@dataclass(frozen=True, slots=True)
class Catalog:
    observations: tuple[Observation, ...]
    _raw: tuple[tuple[str, str], ...]

    def result(self, source):
        return json.loads(dict(self._raw)[source])

    def raw_results(self):
        return {source: self.result(source) for source, _ in self._raw}

    def resolve(self, observation_id):
        for observation in self.observations:
            if observation.id == observation_id:
                result = self.result(observation.source)
                return tuple(result[path[1:]] for path in observation.paths)
        raise KeyError(observation_id)


def build_catalog(incident_id, results):
    """Capture the inputs by value, in tool order, for the lifetime of the incident."""
    if set(results) != set(TOOL_NAMES):
        raise ValueError("Expected exactly the three readiness tool results")
    raw = []
    observations = []
    for index, source in enumerate(TOOL_NAMES, start=1):
        result = results[source]
        if result["tool"] != source:
            raise ValueError(f"Tool result does not match source {source}")
        state = result["state"]
        field = "evidence" if state == "ok" else "state"
        kind = _KINDS[source] if state == "ok" else (
            "gap" if state == "missing_evidence" else "collection_error"
        )
        raw.append((source, json.dumps(result, sort_keys=True, allow_nan=False)))
        observations.append(Observation(
            id=f"{incident_id}:{index}",
            kind=kind,
            source=source,
            state=state,
            _value_json=json.dumps(result[field], sort_keys=True, allow_nan=False),
            raw_ref=f"/diagnosis/raw_results/{source}",
            paths=(f"/{field}",),
        ))
    return Catalog(tuple(observations), tuple(raw))

# POC-001 — Pod readiness

The lab uses Python 3.12 or later and the standard library. `ReadinessTools`
loads a versioned JSON fixture and exposes three in-memory queries:
`get_pod_status`, `get_events`, and `get_endpoints`. The code runs outside
the service package and container image. The fictional observations follow
the sequence described in [K8S-008](https://github.com/platform-notes/kubernetes-from-scratch/pull/31).

## Run from the repository root

```bash
python3 -m unittest discover -s tests -p test_poc_001.py -v

python3 - <<'PY'
import json
from poc_001.readiness import ReadinessTools, diagnose

print(json.dumps(diagnose(
    ReadinessTools(), scenario="not_ready", namespace="fictional-lab",
    pod="demo-blocked", service="demo-web",
), indent=2))
PY
```

## Tool contract

Each tool accepts an object with `scenario`, `namespace`, `timeout_ms`,
and one resource identifier. The status and event queries accept `pod`.
The endpoints query accepts `service`. Use one of the three scenario
names from the fixture. Resource identifiers are DNS labels of up to
63 characters. The timeout is an integer from 1 to 1,000 ms.

Each result contains `tool`, `state`, and `evidence`. The states are `ok`,
`invalid_input`, `not_found`, `missing_evidence`, `invalid_fixture`,
`fixture_unavailable`, and `timeout`. An empty list is a valid observation.
A JSON null in the fixture indicates missing evidence. The tool checks the
timeout when the synchronous in-memory query finishes. The initial fixture
read, limited to 16 KiB, occurs outside that budget.

The deterministic diagnosis returns `running_not_ready` when the Pod is
Running with `Ready=false`, a readiness probe failure was observed, and
there are no ready endpoints. It returns `healthy` when the Pod is Running
and Ready and has a ready endpoint. Other cases return `insufficient_evidence`.
The fixture defines the observation window and the relationship between
the Pod and Service. The root cause remains unknown.

## Limits

The queries read only the bundled fixture. They use no network connections,
Kubernetes API, credentials, write operations, or shell commands. The diagnosis
uses a fixed rule. Future local inference requires separate authorization
and validation.

## Mode A · Deterministic report

Run from the repository root. The `-B` option disables Python bytecode writes.

```bash
python3 -B -m poc_001 --mode deterministic --incident-id demo-a \
  --scenario not_ready --namespace fictional-lab --pod demo-blocked --service demo-web
python3 -B -m poc_001 --mode deterministic --incident-id demo-b \
  --scenario healthy --namespace fictional-lab --pod demo-healthy --service demo-web
python3 -B -m poc_001 --mode deterministic --incident-id demo-c \
  --scenario incomplete --namespace fictional-lab --pod demo-unknown --service demo-web
```

Each command queries all three sources exactly once. The immutable evidence
catalog and `diagnose()` use copies of the same results. Choose a distinct
`incident_id` for each incident. Observation IDs use that value as a prefix
and a fixed ordinal for each source. The `raw_ref` field is a JSON Pointer
into `diagnosis.raw_results`. The `paths` field contains pointers relative
to the tool result. The report includes the raw results, observations,
gaps, errors, timings in milliseconds, and `ai.state = "not_used"`.
For the same input and fixture, report contents are stable except for
the measured timings.

### JSON contract

`diagnosis.evidence_ids` lists the supporting observations for a conclusive
classification from `diagnose()`. For `running_not_ready`, it references
the Pod condition, events, and endpoints. For `healthy`, it references
the Pod condition and endpoints. For `insufficient_evidence`, the list is
empty. See `observations` for the available facts and `gaps` and `errors`
for details about degraded collection. Each gap or error has an
`evidence_id` that links to its observation and raw tool result.

`collection_quality` describes the collection independently of the classification.

- `complete` means all three queries returned `ok`, including empty lists.
- `missing_evidence` means at least one source had missing evidence and no query reported an operational error.
- `operational_error` means at least one query reported an operational error. Any missing evidence remains listed in `gaps`.

The CLI prints a JSON report and exits with **0** when collection completes
without operational errors, including when evidence is missing. It exits
with **1** and prints the report if a tool fails. With invalid arguments,
it exits with **2** and writes an error to stderr. In the incomplete scenario,
the Pod remains Running/NotReady and the report lists separate gaps for
events and endpoints. The diagnosis applies to the fictional snapshot.
The root cause remains unknown.

Run the POC tests with
`python3 -B -m unittest discover -s tests -p 'test_poc_001*.py' -v`.

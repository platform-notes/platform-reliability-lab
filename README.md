# Platform Reliability Lab

**Platform Engineering · SRE · Kubernetes · Evidence-driven AIOps**

An independent educational lab for reproducible reliability experiments.
Explore observable service behavior, container delivery controls, and
deterministic incident reporting, with evidence that can be traced back
to the experiment inputs.

**Repository identity:** The current GitHub repository is
[`roger-oliveira86/platform-reliability-lab`](https://github.com/roger-oliveira86/platform-reliability-lab).
The repository was renamed from `sre-reliability-lab`. The GHCR release
pause remains active; publication under the new repository name requires
separate approval. Historical GHCR artifacts retain their original image
path and digest.

Use isolated, disposable lab environments. This project is intended for
educational experiments. Production deployment is outside its validated scope.

## What is implemented

| Lab area | Current capabilities | Entry point |
| --- | --- | --- |
| Observable Python HTTP service | `/`, `/healthz`, Prometheus-compatible `/metrics`, JSON request logs, generated request IDs, and opt-in `/failure` | [Service](src/service.py) and [runbook](docs/runbook.md) |
| Container and CI delivery | Non-root Alpine image with pinned base digest, Python tests, YAML and Kubernetes schema checks, container smoke tests, Trivy scanning, and manual GHCR publication | [Dockerfile](Dockerfile), [verification workflow](.github/workflows/verify.yml), and [publication guide](docs/ghcr-publication.md) |
| Example Kubernetes manifests | Namespace, Deployment, and Service definitions with resource limits and container security settings. Runtime deployment in this repository remains unverified. | [Manifests](k8s/) |
| POC-001 readiness reporting | Fictional snapshots, three read-only tools, immutable evidence catalog, deterministic diagnosis, and explicit collection quality | [POC-001 guide](poc_001/README.md) |

## Architecture

```text
HTTP client -> Python service -> /healthz
                             -> /metrics (Prometheus text)
                             -> JSON logs (stdout)

Local fictional fixture -> Pod status, events, endpoints (one query each)
                        -> frozen tool results
                           -> diagnose()
                           -> immutable evidence catalog
                        -> structured JSON incident report
```

## Quick start

Use Python **3.12+** for POC-001. The service and deterministic report use
the Python standard library.

From the repository root, run the tests and the three fictional scenarios:

```bash
python3 -B -m unittest discover -s tests -v

python3 -B -m poc_001 --mode deterministic --incident-id demo-a \
  --scenario not_ready --namespace fictional-lab --pod demo-blocked --service demo-web

python3 -B -m poc_001 --mode deterministic --incident-id demo-b \
  --scenario healthy --namespace fictional-lab --pod demo-healthy --service demo-web

python3 -B -m poc_001 --mode deterministic --incident-id demo-c \
  --scenario incomplete --namespace fictional-lab --pod demo-unknown --service demo-web
```

| Scenario | Classification | Collection quality |
| --- | --- | --- |
| `not_ready` | `running_not_ready` | `complete` |
| `healthy` | `healthy` | `complete` |
| `incomplete` | `insufficient_evidence` | `missing_evidence` |

POC-001 Mode A queries Pod status, events, and endpoints exactly once from
the bundled fixture. The immutable evidence catalog and `diagnose()` use
the same results. Reports contain supporting observation IDs, raw tool
results, distinct gaps and errors, timings, and `ai.state = "not_used"`.
Mode A uses no LLM, Kubernetes API, external network, or credentials.

`collection_quality` is independent of the classification.
`complete` means every query returned `ok`. `missing_evidence` indicates
at least one gap with no operational error. `operational_error` indicates
a query failed, while any gaps remain visible. In the incomplete scenario,
the Pod is Running/NotReady but events and endpoints are missing.
The report leaves probe failure and Service availability undetermined.
The root cause remains unknown.

See the [POC-001 JSON contract and exit codes](poc_001/README.md#json-contract).

To explore the HTTP service locally:

```bash
python3 -B -m src.service
# In another terminal:
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS http://127.0.0.1:8080/metrics
```

The `/failure` endpoint requires explicit opt-in through
`ENABLE_FAILURE_ENDPOINT=true`. Use it only for a bounded failure drill.
`MAX_CONNECTIONS` defaults to 64 active request handlers (1–4096 accepted); extra
connections receive HTTP 503. Each connection has a 10-second socket timeout.
For Kubernetes, keep `terminationGracePeriodSeconds` (default 30 seconds)
longer than the 10-second socket timeout to allow in-flight requests to finish.
SIGTERM/SIGINT trigger an orderly server shutdown, and interrupted writes
still record request outcomes. The failure switch is read once at server startup;
restart to change it. Request logs and metrics record only known route labels
(or `unmatched`), never raw paths. These limits do not make the demo production-ready.
The service and failure endpoint must never be exposed to public internet
or production traffic. Read the [security policy](SECURITY.md) and
[experiment protocol](docs/experiment.md) first.

## Containers and Kubernetes examples

For an optional local container build, use
`docker build -t platform-reliability-lab:local .`.

The [example Deployment](k8s/deployment.yaml) uses the placeholder
`ghcr.io/YOUR_USERNAME/platform-reliability-lab:VERSION`. A future disposable
cluster experiment requires a reviewed image reference and verification
of the active Kubernetes context. The namespace is
`platform-reliability-lab`, and the Deployment and Service remain
`reliability-demo`. Static schema validation does not establish successful
rollout, runtime security, or availability.

## Delivery and security evidence

- The container runs as UID/GID 10001 with a digest-pinned Python Alpine base.
- The runtime image removes `pip` and the bundled `ensurepip` wheels. The service
  uses only the Python standard library, so no package manager ships in the
  image. This also removes libraries vendored inside `pip` (for example
  `urllib3`, `msgpack` and `setuptools`) that container scanners report as
  vulnerabilities even though the service never imports them.
- Dependabot checks the Docker base image and pinned GitHub Actions weekly.
- `krb5-libs=1.22.3-r0` is an intentionally pinned Alpine security dependency
  included while the selected base image requires a patched Kerberos package.
  Dependabot does **not** update `apk add` version pins. On base-image updates,
  manually check `apk info -v krb5-libs` inside the new build, compare with the
  Alpine security advisory and run the container vulnerability scan. Remove the
  explicit `apk` pin only when the updated base already contains an acceptable
  patched package version, then review the Dockerfile change in a separate PR.
  Never suppress findings or loosen vulnerability gates to complete an update.
- Checkout Actions use a full commit SHA. Trivy uses a pinned image digest.
- PR verification tests Python, checks YAML and Kubernetes schemas, builds
  the container, runs HTTP smoke tests, and scans the image.
- Trivy reports HIGH findings. CRITICAL findings block the workflows.
  A passing workflow does not establish the absence of vulnerabilities.
- The [GHCR workflow](.github/workflows/publish-ghcr.yml) uses
  `workflow_dispatch` with a `main` and exact-repository guard.
  Default permissions are `contents: read`; `packages: write` is scoped
  to the manual publication job.

**Historical verified publication — November 7, 2026**

`ghcr.io/roger-oliveira86/sre-reliability-lab@sha256:4b6013f5ac28b109fbcba868dec2239786c13ce2bfa4f00d20d3bc29d5a60517`

The recorded HIGH/CRITICAL scan for that publication reported zero findings.
That dated result is historical evidence. Current image findings and package
access require their own verification. Existing HIGH findings require
separate evaluation by affected package, fix availability, severity, and
exploitability.

## Planned capabilities

The [incremental platform blueprint](docs/platform-engineering-stack.md)
describes future work. Kubernetes runtime deployment, GitOps reconciliation,
OpenTelemetry, tracing, dashboards, and live SLO measurement remain
undemonstrated in this repository. Backstage is a later optional stage.
AI-assisted Mode B remains unimplemented and requires separate authorization
and validation.

## Operational documentation and learning

- [Service runbook](docs/runbook.md)
- [Controlled experiment protocol](docs/experiment.md)
- [Postmortem template](docs/postmortem-template.md)
- [Publication checklist](docs/publication-checklist.md)
- [Kubernetes From Scratch](https://github.com/roger-oliveira86/kubernetes-from-scratch)
  provides the separate Linux and Kubernetes learning sequence and exercises.
- [From LLM Tool Calling to Deterministic AIOps: Lessons from Kubernetes Troubleshooting](https://dev.to/rogeroliveira86/from-llm-tool-calling-to-deterministic-aiops-lessons-from-kubernetes-troubleshooting-57jb)
  describes the published learning experience.

## Provenance and license

This repository is original independent work, created anew. It is not a fork
or republication of `alanmosilva/sre-observability-course`. Review licenses
and attribution requirements before adding third-party scripts, dashboards,
or images.

Apache-2.0. See [LICENSE](LICENSE).

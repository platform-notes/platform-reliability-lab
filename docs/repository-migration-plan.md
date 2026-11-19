# Controlled repository migration plan

RM-GITHUB-PLATFORM-002 · GOV-002 · November 18, 2026
Status: preparation for owner review. Current repository:
`roger-oliveira86/sre-reliability-lab`. Proposed future repository:
`roger-oliveira86/platform-reliability-lab`.

## Verified starting point

The live `main` was `aa7e341b8e94551b4d8f4a90df6983ed9664e797`,
the merge commit of PR #13. No open PRs were returned at preflight.
The isolated checkout was clean. The [root README](../README.md) describes
the current identity and the proposed future name correctly.

This preparation adds only this plan. The current publisher retains its
exact repository guard and its computed image path. POC-001 Mode A uses
the original three fictional fixtures, `diagnose()`, the immutable catalog,
and the [English report contract](../poc_001/README.md#json-contract).
Its collection qualities remain `complete`, `missing_evidence`, and
`operational_error`, with `ai.state = "not_used"`.

Historical verified publication, **November 7, 2026**:

`ghcr.io/roger-oliveira86/sre-reliability-lab@sha256:4b6013f5ac28b109fbcba868dec2239786c13ce2bfa4f00d20d3bc29d5a60517`

This reference always retains its original path and digest. Its dated scan
is historical evidence. Current package access and vulnerability status
require independent verification.

## Dependency matrix

The classifications below describe future decisions. This preparation
changes only the plan.

| Dependency and source | Classification | Cutover decision |
| --- | --- | --- |
| Current GitHub URL in [README](../README.md) | Must change at cutover | Update active identity wording and maintained links after verifying the new URL. |
| GitHub web URLs, issue/PR links, and local Git remotes | Must change at cutover for active clients | Verify redirects and existing issue/PR references. Update each maintained clone explicitly. Historical citations may retain their original URL. |
| Historical OCI reference in README and this plan | Historical evidence—never change | Preserve original package path, digest and date. |
| GHCR package naming, visibility and ACLs | Unknown | Establish ownership, permissions, repository association and consumer access before selecting a future package strategy. Repository redirects do not establish package migration. |
| Publisher `github.repository` guard in [publish-ghcr.yml](../.github/workflows/publish-ghcr.yml) | Must change at cutover | Review the exact-name change below. Keep the manual trigger and `main` requirement. |
| Publisher `REPO`, computed image name and OCI source/revision labels | Must review at cutover | `REPO` comes from `github.repository`. Future publication would target `ghcr.io/roger-oliveira86/platform-reliability-lab:sha-<12 chars>` and a new source URL. That package has no verified publication in this review. Existing labels remain historical. |
| Commands and image examples in [publication guide](ghcr-publication.md) | Must change at cutover for active commands | Update `--repo` arguments after rename. Choose package examples only after package access and publication strategy are approved. |
| Local Docker tag `sre-reliability-lab:local` | Updated by AUDIT-FIX-04 | Local example renamed to `platform-reliability-lab:local`; the older tag is retained here only as historical migration context. |
| Placeholder image in [Deployment](../k8s/deployment.yaml) | Updated by AUDIT-FIX-04 | The placeholder is now `ghcr.io/YOUR_USERNAME/platform-reliability-lab:VERSION`. This does not authorize publication or deployment; existing GHCR image paths and digests remain historical. |
| Namespace `sre-reliability-lab`, workload/Service `reliability-demo` | Updated by AUDIT-FIX-04 | Namespace renamed to `platform-reliability-lab`; Deployment and Service names remain `reliability-demo`. Runtime rollout is still unverified. |
| HTTP service identity and its assertion in [service](../src/service.py) and [test](../tests/test_http.py) | Updated by AUDIT-FIX-04 | Response identity and assertion now use `platform-reliability-lab`. Previous value is historical migration context only. |
| Starter archive filename in [gitignore](../.gitignore) | Safe to preserve forever | Retain the historical filename exclusion. |
| README relative links and workflow file paths | Safe to preserve forever while paths exist | Validate after cutover. They do not depend on repository name. No repository-name badges were present in this repository. |
| DEV.to article and LinkedIn/profile backlinks | Unknown | Review the published [DEV.to article](https://dev.to/rogeroliveira86/from-llm-tool-calling-to-deterministic-aiops-lessons-from-kubernetes-troubleshooting-57jb) and owner-managed profile/LinkedIn content after cutover. No external account edits are part of preparation. Full backlink coverage is unverified. |
| [Kubernetes From Scratch](https://github.com/roger-oliveira86/kubernetes-from-scratch) and K8S-008 PR reference | Safe to preserve forever | Keep the distinct learning repository and existing POC reference. Companion source is read-only. |
| Webhooks, applications, CI consumers and package integrations | Unknown beyond visible inventory | Recheck integration subscriptions, repository IDs, slugs, permissions and delivery status at cutover. |
| Checkout action SHA, base-image/Trivy digests, Kubeconform schema sources and external blueprint links | Safe to preserve independently of rename | Retain the pins and current URLs. Updates require their own justification. |

## Read-only access and security inventory

These observations are a preflight snapshot, not a guarantee of cutover state.

| Read surface | Observed result | Required follow-up |
| --- | --- | --- |
| Current repository | Public; default `main`; existing credential reports admin/read/write repository permissions | Owner approval remains required for mutations. |
| Target repository read API | HTTP 404 for the proposed slug | Availability is unverified. A 404 can conceal inaccessible data. Confirm availability with the owner immediately before Gate B. |
| Ruleset `26776642` | Active on the default branch; strict required `checks`, PR required, thread resolution, squash merge, deletion/force-push blocked, no bypass actors; required approving review count is 0 | Preserve controls. Obtain explicit technical/owner review. A configured PR requirement alone does not require an independent approval. |
| Legacy branch-protection endpoint | HTTP 404, “Branch not protected” | This endpoint does not describe the active ruleset above. Recheck effective rulesets at cutover. |
| Default workflow permissions | Read; workflow approval of PR reviews disabled | Retain current defaults and job-specific package-write scope. |
| Existing CLI token scopes | `gist`, `read:org`, `repo`, `workflow` | No scope expansion requested. Publication continues to use its job's `GITHUB_TOKEN`. |
| Package list and package detail | HTTP 403 requiring `read:packages` | Package visibility, ACLs, associations and versions remain unknown. Owner must verify them before cutover. |
| Open Dependabot alerts | Successful read returned an empty array | This covers that API's open alerts only. Container findings still need review. |
| Code-scanning alerts | HTTP 404, “no analysis found” | No code-scanning assurance follows from this response. |
| Repository hooks | Successful read returned an empty array | Recheck at cutover; this does not enumerate all application integrations. |
| Application installations | HTTP 404 from attempted repository installation inventory | Application inventory remains unverified. Require owner review. |
| Secret scanning / push protection / Dependabot security updates | Enabled in visible repository settings | Secret values were not read. Any integration-specific credential configuration requires owner verification. |
| Prior PR CI | [Run 44416084930](https://github.com/roger-oliveira86/sre-reliability-lab/actions/runs/44416084930), source head `8712fed5700aa6f836d0eb204f6584528a94e60f`, completed successfully | Existing scan reported **16 HIGH, 0 CRITICAL**, all listed findings in `krb5-libs`. Fix availability and exploitability were not assessed here. |

The [publisher](../.github/workflows/publish-ghcr.yml) uses
`workflow_dispatch`, requires `refs/heads/main`, and allows only
`roger-oliveira86/sre-reliability-lab`. The baseline is `contents: read`;
`packages: write` belongs only to its manual publication job.
The CRITICAL block, SHA-pinned checkout and digest-pinned Trivy remain
the current controls. A successful check does not establish zero vulnerabilities.

## Compatibility decision

Retain the workflow as implemented. A Python truth table for an analogous
expression would not establish GitHub's actual expression evaluation or
package authorization. Current-name publication eligibility is preserved
by keeping the workflow bytes identical.

A two-name allowlist was considered. It would permit the future identity
before package access and cutover were reviewed. The narrow exact-name
replacement is the proposed later patch, **only after Gate B permits the
actual rename and its coordinated follow-up PR**:

```diff
-    if: github.ref == 'refs/heads/main' && github.repository == 'roger-oliveira86/sre-reliability-lab'
+    if: github.ref == 'refs/heads/main' && github.repository == 'roger-oliveira86/platform-reliability-lab'
```

This is a documentation example, not an applied patch. Keep the publisher
paused through the rename window until the reviewed guard matches the
actual repository name and package checks are complete. Do not dispatch
the workflow to test eligibility.

## Cutover sequence and manual approval gates

1. Review this compatibility PR, its diff, local evidence and automatic PR CI.
   Resolve any preparation blockers.
2. **Gate A — explicit owner approval to merge the final compatibility PR.**
   The current order ends at PR review. An approved merge incorporates only
   documentation and has no publishing or runtime effect.
3. Before Gate B, refresh the current SHA, destination availability, rulesets,
   open PRs, integrations, Git remotes, package ACLs and consumers. Resolve
   the unknown package and installation inventory with the owner. Review HIGH
   findings by severity, package, fix availability and exploitability.
4. **Gate B — explicit owner approval for the actual rename, exact metadata
   updates, and post-rename verification.** Agree the publication pause,
   follow-up PR scope, rollback owner and checks before execution.
5. After the separately authorized rename, verify the actual slug and stage
   the narrow guard patch plus active documentation/link changes in a separate
   PR. Its merge requires explicit approval. Until reviewed and merged, the
   old guard will skip publication under the new identity.
6. Verify old web/Git redirects, issue/PR continuity, effective rulesets,
   current PR CI, active links, local remotes and visible integration status.
   Confirm package identity, association and access using authorized reads.
   Preserve existing images and labels.
7. A new image, new package, package-permission mutation or publication
   requires a separate explicit approval. Deployments require another
   explicit approval. Neither gate authorizes a workflow dispatch by itself.

Proposed future metadata is unchanged from RM-GITHUB-PLATFORM-001:
`platform-reliability-lab`; description “Hands-on Platform Engineering and
SRE labs exploring Kubernetes reliability, observability, CI/CD security,
and evidence-driven AIOps.” Topics are `platform-engineering`, `sre`,
`kubernetes`, `observability`, `aiops`, `devsecops`, `github-actions`,
`python`, `cloud-native`, and `reliability-engineering`.
Keep public visibility, Apache-2.0 and `main`.

## Rollback matrix

| Layer | Response to a failed cutover | Limitation |
| --- | --- | --- |
| GitHub repository name | Stop publication and obtain owner approval before attempting a rename back | The old name may no longer be available. Reusing it can invalidate existing redirects. |
| Reviewed code/documentation | Revert the applicable commit through a reviewed PR; require approval for merge | Restoring a guard for the wrong actual slug will leave publication ineligible. Coordinate rollback with identity. |
| GHCR packages | Preserve old packages and immutable digest references; continue using an approved existing digest where applicable | Repository rename does not establish package rename, access or redirection. No package deletion, retagging or overwrite is an automatic rollback. |
| Integrations and clients | Restore approved URLs/configuration per affected client, then verify delivery/access | Webhooks, app subscriptions, action references and external backlinks may require individual fixes and permissions. |

GitHub documents web and Git redirects, with exceptions for project-site
URLs and hosted Actions. Reusing the old repository name can break redirects.
Verify consumers directly. [GitHub rename guidance](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)

Container packages have their own names, repository associations and
granular access controls. Verify these before any publication decision.
[Container registry guidance](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## Validation without GitHub mutations

Run these local checks from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B -m poc_001 --mode deterministic --incident-id demo-a --scenario not_ready --namespace fictional-lab --pod demo-blocked --service demo-web
python3 -B -m poc_001 --mode deterministic --incident-id demo-b --scenario healthy --namespace fictional-lab --pod demo-healthy --service demo-web
python3 -B -m poc_001 --mode deterministic --incident-id demo-c --scenario incomplete --namespace fictional-lab --pod demo-unknown --service demo-web
git diff --check
```

Expected pairs are `running_not_ready/complete`, `healthy/complete`, and
`insufficient_evidence/missing_evidence`. Every report retains
`ai.state = "not_used"`. Check newly edited Markdown links and anchors,
and compare unchanged source, fixtures, workflows and historical references
against the recorded base. No YAML changed in this preparation.

For the preserved guard, inspect the exact workflow text and manually review
the current-name/main, current-name/feature, arbitrary-repository/main and
proposed-name/main cases. Only current-name/main is eligible at present.
Triggering still requires an explicit manual dispatch. Actual hosted
expression behavior and package authorization require later review.

GitHub-side verification uses read-only repository, ruleset, PR, CI and
package reads. No settings writes, deployment, scan dispatch or publishing
is needed. Automatic existing PR CI may run after submission and its actual
result must be recorded separately. Missing administrative data is a
cutover blocker for the owner to resolve.

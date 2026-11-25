# GHCR publication — controlled, manual release

**Status:** Implemented and verified on November 7, 2026. Publication remains manual from protected `main`.

## Why manual publishing?

Image publication is separate from PR validation. This workflow is started deliberately from the protected `main`, never from a feature branch. The release tag identifies a Git commit (`sha-<12 chars>`), avoiding a mutable `latest` tag.

## Release procedure

**Release pause active:** The commands below are a future release procedure,
not authorization to publish. Dispatch requires separate owner approval to
lift the pause and publish under the new repository identity. The workflow
now derives `ghcr.io/platform-notes/platform-reliability-lab` from the
repository name; publication and access for that path remain unverified.
Existing historical images stay under `ghcr.io/platform-notes/sre-reliability-lab`.

1. Review the PR, check the required `checks` job and squash-merge into protected `main`.
2. Run `gh workflow run publish-ghcr.yml --repo platform-notes/platform-reliability-lab --ref main`.
3. Run `gh run list --repo platform-notes/platform-reliability-lab --workflow publish-ghcr.yml --limit 3` and inspect the successful run summary for the published digest.
4. Confirm the package is associated with the correct GitHub repository. GHCR packages may initially be **private**; review visibility and package access under GitHub Packages. Do not assume public access.
5. Use the exact image path and digest recorded by the approved publication when updating `k8s/deployment.yaml` **in a separate PR**. The placeholder in the current manifest is intentionally left unchanged.
6. Test the image in a disposable cluster, capture the rollout, and record cleanup. Do not use a production cluster.

## Security and scope

- The publisher uses `GITHUB_TOKEN`, not a stored personal access token, and grants `packages: write` **only to the publish job**.
- Checkout is pinned to a full commit SHA. The workflow cannot publish from a PR ref.
- Trivy scans the built image before publication. CRITICAL findings and scanner failures block publication; HIGH findings are reported.
- Signed provenance, SBOM and runtime Kubernetes validation are not implemented.
- The blocking behavior for CRITICAL findings has not been tested with an intentionally vulnerable image.
- The existing PR validation runs on all PRs and is required by the `main` ruleset.

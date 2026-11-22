# AGENTS.md

Instructions for AI agents (Claude Code, Codex, etc.) working in this repository.

## Scope

- One task per session, with a clear definition of done before starting.
- Minimal diff: change only what the task requires.
- Do not touch CI/CD workflows, dependencies, or files outside the task's scope without explicit authorization.

## Validation before merge

- The repository's required check must pass: `checks` (workflow `verify.yml`).
- When there is a runtime image: Trivy must report 0 HIGH/CRITICAL vulnerabilities.
- Container images must be pinned by digest, not a mutable tag.
- Workloads must run as non-root.

## Never

- Push directly to the `main` branch.
- Publish images to GHCR (pause currently in effect).
- Commit secrets, tokens, personal email, or other personal data.
- Rewrite history (force-push, rebasing already-published commits, etc.).

## Review

- Codex comments on the PR.
- Merge is performed by the repository owner, only with green CI.

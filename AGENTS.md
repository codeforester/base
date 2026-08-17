# AI Agent Guidance

This file gives coding agents the repository-specific rules for Base. It is a
navigation layer over the existing contributor docs, not a replacement for
them.

## Working Agreement

- Follow `CONTRIBUTING.md` for workflow and `STANDARDS.md` for code standards.
- Keep Base focused as the local operating contract for deterministic readiness
  and handoff across independent Git repositories. Its durable loop is
  inventory -> prepare -> verify -> trust -> onboard -> hand off.
- Keep project-specific setup, service code, and application behavior in the
  owning project repository unless Base is explicitly the right shared layer.
- Adopt external agent workflow ideas only after translating them into
  Base-specific guidance. Do not vendor or require a third-party methodology
  when a smaller Base-native rule is enough.
- When the user explicitly says a session is design-only or asks for no code
  changes, stay in discussion mode and do not edit files.
- Surface unresolved product or architecture decisions instead of silently
  choosing defaults for broad changes.

## GitHub Workflow

Before implementation, complete the [pre-edit workflow
gate](docs/github-workflow.md#pre-edit-workflow-gate) and work from the
issue-backed worktree. Use the [GitHub Workflow](docs/github-workflow.md) for
the canonical issue, repo-named Project, branch, worktree, pull request, and
cleanup policy, including [superseded pull
requests](docs/github-workflow.md#superseded-pull-requests). This file adds
only the agent-specific repository guidance below.

## Repository Release Contract

Repositories that publish versioned artifacts should opt into Base's release
standardization with `basectl repo configure --release --repo <owner/name>`.
This adds missing release metadata to `base_manifest.yaml` and a
`docs/release-process.md` guide without overwriting repository-specific release
content. Use `basectl repo check --release` to verify adoption, and read the
generated release guide before preparing a release.

## Validation

- Run the narrowest relevant checks first, then broaden when shared behavior is
  touched.
- For bug fixes, reproduce the symptom and identify the root cause before
  changing code. Prefer one focused hypothesis and one focused fix at a time.
- Do not claim work is fixed or complete without fresh verification output from
  the current checkout or worktree.
- For documentation-only changes, run `git diff --check`.
- For general Base changes, run `basectl test base` and `git diff --check`.
- For shell changes, include the relevant BATS tests and ShellCheck when
  available.
- For Python changes, run the relevant pytest target with Base's existing
  `PYTHONPATH` conventions.
- For setup, doctor, workspace discovery, profile, runtime shell, or
  cross-command behavior, run the matching integration checks described in
  `docs/testing.md`.
- If a required check cannot be run locally, say so in the PR and final
  summary.
- For review feedback, verify the suggestion against Base's architecture,
  product boundaries, and existing tests before implementing it.

## AI Context Maintenance

- Treat `.ai-context/` at the repository root as the AI-facing orientation layer
  for Base.
- Use `basectl export-context base --print` to view the current context pack, or
  `ls .ai-context/` to inspect available context files. When
  `.ai-context/INDEX.md` exists, it controls export ordering.
- For every meaningful PR, decide whether `.ai-context/` needs an update and
  state the result in the PR body.
- Update `.ai-context/` when a change affects Base's product shape,
  architecture, command surface, workflows, manifest model, release status, or
  durable design decisions.
- Usually leave `.ai-context/` unchanged for typo-only edits, formatting-only
  edits, test-only changes with no product behavior impact, or internal
  refactors that do not change public behavior or architecture.
- Keep `.ai-context/` public-repo-safe: no secrets, API keys, tokens, private
  local paths, customer data, or personal notes.
- Canonical docs remain the source of truth. If `.ai-context/` disagrees with
  the repo docs or code, update `.ai-context/`.

## Change Boundaries

- Keep public launchers in `bin/` thin.
- Keep Bash command implementations under `cli/bash/commands/<command>/`.
- Keep Base-owned Python command packages under `cli/python/` and shared
  framework integration here; the reusable `base_cli` framework is maintained
  in the standalone `base-cli` repository.
- Use structured parsers or existing Base helpers instead of ad hoc text
  manipulation when the repo provides one.
- Keep stdout for user or automation output; send logs and diagnostics to
  stderr.
- Do not rely on `set -e`, `set -u`, or `set -o pipefail` in Base shell code.
- Do not add repo-level Codex settings for personal model, approval, or sandbox
  defaults. Those belong in the user's Codex configuration unless the change is
  explicitly about shared repository runtime behavior.

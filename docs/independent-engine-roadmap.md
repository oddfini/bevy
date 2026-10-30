# Independent engine roadmap

Owner decision, 2026-10-30: evolve `oddfini/bevy` as an independent engine fork
using the existing Bevy code. The owner delegates implementation, tests, commits,
and PR preparation to agents. Code review and observed verification remain required.
Official Bevy acceptance does not govern the roadmap.

## Product boundary

The first goals are practical AI-assisted game development and reliable mobile
games. Teratorn is the first consumer. Keep rules, game AI, private content,
accounts, credentials, and service-specific code in their game repositories.
Engine APIs may evolve with a documented consumer and recovery plan.

Use existing working renderer, ECS, text, audio, asset, and platform foundations.
Add or replace modules when a reproduced limit or measured benefit justifies it.
We are not starting a complete engine rewrite. Do not rename packages, rebrand
upstream authors' work, or promise support for untested platforms.

## First milestones

1. Establish this independent contribution contract and preserve provenance,
   patch records, exact-source receipts, required checks, and PR protection.
2. Fix observed failures in the existing agent workflow. Prefer small changes
   that make state inspection, commands, cleanup, and evidence reliable. Define
   the failure before adding a feature or replacing a subsystem.
3. Improve development-state inspection, input/capture workflows, and reproducible
   diagnostics when a real consumer needs them. Keep development endpoints
   separate from production game authority and private state.
4. Improve mobile input, lifecycle, and performance from measured game failures.
   Headless tests do not qualify rendering, input, or phone behavior.

This list is a priority order, not a claim that the features or platform checks
are complete. Each implementation PR supplies its own evidence and scope.

## Contribution and adoption

Use one focused `codex/` task branch and a PR against `codex/teratorn-ai`, the
current verified integration branch. Keep `main` as the existing reference branch
until a separate transition is requested. AI-authored implementation and prose
are accepted; disclose the actual implementation and review roles. The owner is
not expected to manually write every commit or PR description.

Run relevant failure regressions and required checks. Reuse passing results only
while their inputs remain valid. Respect approved cost and execution limits;
do not bypass a blocked check or replace its result with an invented status.
Preserve the original upstream history, licenses, credits, and recorded patches.
Current protected-file guards still apply. Evolving them requires a separate
reviewed change with negative cases.

Merge an engine PR only after its checks and review pass. Game adoption is a
separate PR that selects an exact engine SHA and checks the affected game paths.
Tool-only updates do not raise a game's engine pin. Native, headless, and device
evidence remain distinct. No engine merge implicitly authorizes a server change,
new credentials, publishing packages, or a store release.

The existing Teratorn TestFlight 218 source and engine pin stay frozen. Its current
release worktrees, signing inputs, compiled output, and pending owner actions are
outside this engine-policy change.

## Optional upstream intake

Select exact upstream commits when they benefit this roadmap. Record their
source, authorship, adaptations, and interactions with local changes. Preserve a
known working engine revision for rollback. Verify an equivalent upstream fix
before marking a local patch superseded. Upstream issues and PRs require their
own authorization and must follow the upstream project's policies.

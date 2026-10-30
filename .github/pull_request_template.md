<!-- This template is for oddfini/bevy. Read CONTRIBUTING.md and AGENTS.md. -->

## Problem and result

Describe one behavior change. Give the reproduction or expected result.

## Implementation

Explain the smallest useful change and name the exact PR base SHA. For an
independent change, state the design and why it serves our roadmap. For upstream
intake, link the original source SHA, preserve authorship, and explain adaptations.
Record internal changes in the patch policy.

## Consumer and resource impact

Name affected packages and public APIs. State whether any game pin must change and
which consumers were actually checked. Describe migration or replacement tests for
breaking changes. State build/CI/provider scope and any required new authority;
this PR does not authorize deployment or a game release.

## Verification

List actual commands, results, platform, and evidence paths. State what remains
untested. Runtime input changes require a current native receipt.

- [ ] Fast checks passed.
- [ ] A regression test covers the bug or new behavior.
- [ ] Affected engine tests and native evidence are current when required.
- [ ] Existing behavior, error paths, and the final diff were reviewed.
- [ ] Unrelated changes and unused abstractions were removed.

## AI use and review

State how AI was used. Name an independent reviewer only if one actually reviewed.
AI-generated code, tests, and prose are allowed in this fork.

## Recovery

State how to undo the behavior change. Link the previous verified SHA for an
upstream baseline update. Keep game dependency changes in a separate game PR.

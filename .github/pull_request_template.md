<!-- This template is for yongjip/bevy. Read CONTRIBUTING.md and AGENTS.md. -->

## Problem and result

Describe one behavior change. Give the reproduction or expected result.

## Implementation

Explain the smallest useful change. For an engine patch or upstream update, link
the original source SHA, explain adaptations, and update the patch policy.

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

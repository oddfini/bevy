# Maintaining the downstream fork

The verified engine base and internal changes are recorded in
[policy.json](policy.json). This independently maintained fork may accept its own
engine designs, APIs, and development features. Reuse tools, `examples/agent/`, and
plugins where they fit. Record engine changes and their consumer impact; upstream
acceptance is not a promotion condition. See [the roadmap](../independent-engine-roadmap.md).

## Controls

- `maintenance.py check` compares internal changes with recorded file hashes.
  An extra engine file or an unrecorded edit fails. Each patch needs an exact source
  commit, a reason, and a regression test. Adapted source needs an explanation.
- The same check preserves upstream package names, original remote examples,
  license files, credits, upstream README, and existing workflow files. The root
  Cargo manifest may only append the recorded downstream example targets.
  These are current machine protections, not an already-removed compatibility
  policy. A protected-structure change needs a reviewed guard change and negative tests.
- Native receipts bind the base/patch policy, manifests, lockfile, every downstream
  example file, driver, and gate to their source hashes. They also bind screenshot
  contents and dimensions. Sources changing during a run make that run fail.
- `downstream-ready` is the branch protection status. The workflow runs Python
  guard regressions, Rust transition tests, source/evidence checks, and formatting.
  Engine, dependency, and maintenance pipeline changes also run engine package
  tests and Clippy. Workflow dispatch can
  request all recorded engine checks with `engine_tests=true`.
- Fork settings disable inherited upstream automation. Files stay intact for
  future updates. Keep only `Downstream maintenance` enabled unless a new workflow
  has a concrete purpose and its permissions, cost, and triggers were reviewed.
- CI pins Ubuntu 24.04, Rust 1.99.1, and action commit SHAs. Change the OS, toolchain,
  or lockfile deliberately and rerun the selected checks. Cache keys include the
  OS label, Rust version, and lockfile hash.

Branch protection requires a PR, an up-to-date passing status, and resolved review
discussions. Apply it to administrators too. Disable force pushes and branch
deletion. No separate human approval is required for routine authorized work.
The repository owner can still change these settings. These controls catch mistakes;
they do not replace review or protect against an owner changing the controls.

Check hosted settings after changing the workflow or repository configuration:

```sh
gh api repos/oddfini/bevy/actions/workflows
gh api repos/oddfini/bevy/branches/codex%2Fteratorn-ai/protection
```

## Propose an independent change

Start from the verified integration branch and create a `codex/` task branch.
Record the current base SHA, the observed requirement, intended behavior, affected
packages and consumers, regression checks, and recovery steps. A downstream change
does not need an upstream PR or original upstream implementation. Record its own
source commit with `origin: downstream`; keep the existing file-hash and adaptation
rules. An API change also needs a migration or an explicit supported-consumer boundary.

Keep the implementation, review, and observed validation roles clear when agents
perform the work. Do not report self-review as independent review. A contribution
task does not authorize new spending, credentials, provider actions, game pin
changes, or store releases outside its approved scope.

## Select an upstream change

1. Start from the verified downstream branch. Create a `codex/` task branch.
2. Read the upstream commit and its issue/PR. State the feature or reproduced bug
   that this project needs. Do not import unrelated updates just because they exist.
3. Fetch the exact upstream commit. Replace `FULL_SOURCE_SHA` below with its full
   40-character SHA. The planner reads local Git objects and does not fetch or apply.

```sh
git fetch --no-tags upstream FULL_SOURCE_SHA
python3 -B tools/maintenance.py plan FULL_SOURCE_SHA
```

The plan reports changed files and overlaps with active patches. The source commit
must come from the official upstream repository. For a single commit, use
`git cherry-pick -x FULL_SOURCE_SHA` on the task branch. Keep adaptations small.
Record `origin: upstream`, the original SHA, why it is needed, its regression, final
file hashes, and an `adaptation` explanation when the final source differs.

For a broader baseline update, use `plan FULL_SOURCE_SHA --mode baseline`. Integrate
the exact commit on the task branch and update `base` in the policy. Refresh the
preserved upstream README, protected files, and Cargo prefix from that revision.
Retain the downstream example declarations. Test all changed packages by passing
the PR's previous base SHA to `test-engine --since`.

## Verify and promote

1. Reproduce the original bug on the old implementation when feasible. Keep the
   regression test. For a feature, test its expected result and rejected inputs.
2. Resolve patch overlaps by behavior. If upstream now provides the same fix,
   rerun the local regression tests. Mark the local record `superseded` with an
   empty `files` map only when no override remains. Preserve the fixed behavior.
3. Run the contribution checks. Refresh native evidence when its inputs change.
   Update platform/game tests when those paths are affected. Headless checks alone
   do not establish rendering, phone input, or game compatibility.
4. Review and merge the candidate PR after required checks pass. Preserve published
   history. Keep the previous verified revision in Git as the rollback reference.
5. Update a game's exact engine SHA in a separate game PR. For Teratorn, compare
   the Rust game result with the existing C# reference before adopting the update.

If a candidate fails, keep the verified branch and game pin unchanged. Fix the
candidate on its task branch or abandon it with a reason. If a merged update
regresses, revert the downstream integration through a tested PR. Never force
rewrite published history or undo an older fix without testing its replacement.

Upstream Bevy submissions remain a separate action under upstream rules. This
procedure and this fork's AI policy do not authorize an upstream issue or PR.

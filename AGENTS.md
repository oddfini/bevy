# Agent guide for oddfini/bevy

This is Oddfini's independently maintained engine fork, based on Bevy.
Its roadmap serves AI-assisted game development and Oddfini games. Official Bevy
acceptance is not a prerequisite for a downstream feature or design decision.
Read `FORK.md` before changing engine code. Preserve upstream history, licenses,
copyright notices, and third-party credits.

## AI-assisted work in this fork

- AI may write code, tests, documentation, commit messages, issues, and PR text
  submitted to `oddfini/bevy`. The owner need not rewrite generated prose or
  manually author each commit. Follow the user's authorization for external
  actions. This permission does not itself authorize publishing or merging.
- Review generated changes. Report what changed, what was tested, and remaining
  limits. Never claim a build, device run, or test that was not observed.
- Keep engine patches small. Keep Teratorn rules, content, credentials, and private
  game assets outside this engine repository.
- Reuse Bevy systems before adding abstractions. Do not turn a game-specific
  adapter into a general framework without a concrete need.

## Develop the independent engine

- Reuse working Bevy subsystems. Build tools and plugins where they meet the need.
  Independent engine features, internal designs, and API changes may also be proposed.
  Choose their scope from an observed game or development requirement.
- An internal or API change needs a stated result, affected packages and consumers,
  regression tests, compatibility impact, and a recovery plan. Isolate it from
  unrelated refactors and record its purpose and source in `FORK.md` and the patch policy.
- Current package names, original examples, root Cargo manifest, workflows, and
  provenance protections remain enforced by `maintenance.py`. This policy change
  does not remove those checks. A change to a protected structure requires its own
  reviewed guard update and negative regressions; do not edit evidence to hide a failure.
- Evaluate upstream updates on a task branch against an exact revision. Keep the
  currently verified revision until the selected checks pass. Upstream intake is
  optional and must serve the independent roadmap. Check
  game compatibility before changing a game's pinned engine dependency.
- When upstream contains an equivalent fix, verify its behavior and mark the
  downstream patch as superseded. Preserve the fixed behavior; do not undo a fix
  just to remove an old patch commit. Do not rewrite published history.

## Verification

Follow `CONTRIBUTING.md` for every change. `docs/maintenance/policy.json` is the
machine-readable base and engine patch record. Use `tools/maintenance.py plan`
before adopting an upstream commit. Keep original source SHAs and adaptations.
Do not update a record or weaken a test solely to hide a failing check.

Use task branches and PRs against `codex/teratorn-ai`. The required hosted status
is `downstream-ready`. Do not bypass branch protection, push directly to the
verified branch, or enable inherited release/deployment workflows for convenience.
Keep the current branch names until a separate branch transition is requested.
Follow [the roadmap](docs/independent-engine-roadmap.md) for scope and adoption boundaries.

Run the guard regressions and fast Rust model tests from `CONTRIBUTING.md`.
Use Python `-B` for tools and tests. Entry points must disable local bytecode before
importing helpers under `tools/`; `tools/*` also discovers Rust workspace members.
When engine files change, use `maintenance.py test-engine --since` with the exact
PR base SHA. This includes every changed package, including an upstream baseline
update. When runtime inputs change, run `agent-loop.py` with its checks/build
enabled, then validate/copy evidence with `maintenance.py record`. A stale receipt
must fail. Keep native runtime evidence separate from hosted headless results.

For the button patch, run:

```sh
cargo fmt -p bevy_ui_widgets --check
cargo test -p bevy_ui_widgets --locked
cargo clippy -p bevy_ui_widgets --all-targets --locked -- -D warnings
```

For the agent-loop example, use the focused test command in `README.md` and run
`python3 tools/agent-loop.py` for actual input, domain state, and screenshot proof.
Reserve a shared desktop before windowed runs when the local project requires it.
Do not treat a successful command invocation or screenshot alone as behavioral proof.

Use matching checks for other changed crates. Changes to rendering, input, or
mobile behavior also need relevant runtime evidence. Headless tests do not prove
phone behavior. Reuse passing checks while their inputs are unchanged.

## Upstream boundary

The upstream Bevy contribution and AI policies still apply to submissions and
communication in `bevyengine/bevy` and its communities. This fork's permission to
use AI-generated prose does not apply there. Obtain the user's instruction before
opening an upstream issue or PR; prepare the evidence first.

Use `codex/` task branches. Push only to the user's fork unless another target
was explicitly authorized. Do not push to or rewrite upstream branches.
